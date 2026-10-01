import asyncio
from dataclasses import replace
from datetime import date
import json
import logging

import httpx
import pytest

from app.main import create_app
from app.realtime_policy.provider import DisabledRealtimeSearchProvider
from app.realtime_policy.tavily import TavilyProviderError, TavilyRealtimeSearchProvider
from test_real_workflow_tools import settings


async def _search(handler, *, limit: int = 5):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = TavilyRealtimeSearchProvider(
        api_key="test-key",
        timeout_seconds=0.2,
        client=client,
    )
    try:
        return await provider.search(
            "苏州毕业生最新就业政策",
            ["suzhou.gov.cn", "hrss.suzhou.gov.cn"],
            limit,
        )
    finally:
        await client.aclose()


def test_tavily_maps_response_and_sends_restricted_official_domains() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://api.tavily.com/search"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["query"] == "苏州毕业生最新就业政策"
        assert payload["include_domains"] == ["suzhou.gov.cn", "hrss.suzhou.gov.cn"]
        assert payload["include_domains_mode"] == "restrict"
        assert payload["max_results"] == 5
        assert payload["search_depth"] == "basic"
        assert payload["language"] == "zh-cn"
        assert payload["include_published_date"] is True
        return httpx.Response(200, json={"results": [{
            "title": "苏州高校毕业生就业政策清单",
            "url": "https://www.suzhou.gov.cn/policy",
            "content": "官方政策摘要",
            "published_date": "Tue, 30 Sep 2026 08:00:00 GMT",
        }]})

    results = asyncio.run(_search(handler))

    assert len(results) == 1
    assert results[0].title == "苏州高校毕业生就业政策清单"
    assert results[0].url == "https://www.suzhou.gov.cn/policy"
    assert results[0].snippet == "官方政策摘要"
    assert results[0].publishedAt == date(2026, 9, 30)


def test_tavily_keeps_missing_or_unreliable_published_date_as_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [
            {"title": "无日期通知", "url": "https://www.suzhou.gov.cn/a", "content": "摘要"},
            {"title": "日期不可靠", "url": "https://www.suzhou.gov.cn/b", "content": "摘要", "published_date": "最近发布"},
        ]})

    results = asyncio.run(_search(handler))

    assert [item.publishedAt for item in results] == [None, None]


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_tavily_http_errors_fail_without_retry(status_code: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, json={"detail": {"error": "secret provider detail"}})

    with pytest.raises(TavilyProviderError) as exc_info:
        asyncio.run(_search(handler))

    assert exc_info.value.status_code == status_code
    assert calls == 1
    assert "secret provider detail" not in str(exc_info.value)


def test_tavily_timeout_is_translated_for_existing_timeout_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider timed out", request=request)

    with pytest.raises(TimeoutError):
        asyncio.run(_search(handler))


def test_tavily_invalid_json_is_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"Content-Type": "application/json"})

    with pytest.raises(TavilyProviderError) as exc_info:
        asyncio.run(_search(handler))

    assert exc_info.value.status_code is None


def test_tavily_skips_malformed_items_but_keeps_valid_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [
            {"url": "https://www.suzhou.gov.cn/missing-title", "content": "坏数据"},
            {"title": "合法通知", "url": "https://www.suzhou.gov.cn/good", "content": "合法摘要"},
            "not-an-object",
        ]})

    results = asyncio.run(_search(handler))

    assert [item.title for item in results] == ["合法通知"]


def test_tavily_rejects_malformed_results_container() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": {"title": "not-a-list"}})

    with pytest.raises(TavilyProviderError):
        asyncio.run(_search(handler))


def _configured_provider(app):
    return app.state.realtime_search_provider


def test_application_uses_disabled_provider_when_realtime_is_disabled() -> None:
    app = create_app(replace(settings(), realtime_policy_search_enabled=False))
    assert isinstance(_configured_provider(app), DisabledRealtimeSearchProvider)


def test_application_builds_tavily_provider_when_enabled_with_key() -> None:
    app = create_app(replace(
        settings(),
        realtime_policy_search_enabled=True,
        realtime_policy_search_provider="tavily",
        realtime_policy_search_api_key="configured-key",
    ))
    provider = _configured_provider(app)
    assert isinstance(provider, TavilyRealtimeSearchProvider)
    assert provider.timeout_seconds == settings().realtime_policy_search_timeout_seconds


def test_application_missing_tavily_key_is_disabled_without_startup_failure(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="app.main"):
        app = create_app(replace(
            settings(),
            realtime_policy_search_enabled=True,
            realtime_policy_search_provider="tavily",
            realtime_policy_search_api_key="",
        ))

    assert isinstance(_configured_provider(app), DisabledRealtimeSearchProvider)
    assert "realtime search enabled but API key missing" in caplog.text


def test_application_rejects_unknown_realtime_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported realtime policy search provider"):
        create_app(replace(
            settings(),
            realtime_policy_search_enabled=True,
            realtime_policy_search_provider="unknown",
            realtime_policy_search_api_key="configured-key",
        ))
