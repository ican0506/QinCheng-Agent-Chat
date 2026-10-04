from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.base import AgentMessage, AgentToolCall, AgentToolResponse, LLMProvider
from app.web_search.tool import TavilyWebSearchProvider, WebSearchTool
from tests.test_agent_reply import COMPLETE_PROFILE, ScriptedToolProvider, payload, settings


class FakeWebSearchTool:
    """可注入的联网搜索工具替身；记录调用并返回脚本化结果。"""

    def __init__(self, results: list[dict[str, str]] | None = None, fail: bool = False) -> None:
        self.results = results if results is not None else [
            {
                "title": "苏州市创业社保补贴最新申报通知",
                "url": "https://www.suzhou.gov.cn/news/2026-notice",
                "snippet": "2026年度申报窗口将于近期开放，补贴标准为每月1100元。",
            }
        ]
        self.fail = fail
        self.queries: list[str] = []
        self.time_ranges: list[str | None] = []

    async def search(self, query: str, time_range: str | None = None) -> dict[str, Any]:
        self.queries.append(query)
        self.time_ranges.append(time_range)
        if self.fail:
            return {"status": "UNAVAILABLE", "note": "联网搜索暂时不可用", "results": []}
        return {"status": "OK", "results": self.results}


def web_settings(**overrides: object) -> Settings:
    return settings(
        web_search_enabled=True,
        web_search_api_key="tvly-test-key",
        **overrides,
    )


def web_payload(message: str, session: str = "web-search-session") -> dict:
    data = payload(message, COMPLETE_PROFILE, session=session)
    data["webSearch"] = True
    return data


def test_web_search_off_excludes_tool_and_off_request_has_no_sources() -> None:
    provider = ScriptedToolProvider([
        ScriptedToolProvider.text("这是本地知识即可回答的内容。"),
    ])
    client = TestClient(create_app(web_settings(), provider))

    response = client.post("/api/agent/chat", json=payload("本地政策有哪些？", COMPLETE_PROFILE))

    assert response.status_code == 200
    assert "search_web" not in {t["function"]["name"] for t in provider.tool_defs[0]}
    assert response.json()["data"]["sources"] == []


def test_web_search_on_lets_model_search_and_returns_sources() -> None:
    search_tool = FakeWebSearchTool()
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("search_web", '{"query": "苏州创业社保补贴 2026 申报"}', "call-w1"),
        ScriptedToolProvider.text(
            "根据苏州市政府官网最新通知，2026年度申报窗口即将开放，补贴标准仍为每月1100元。"
            "来源：[苏州市创业社保补贴最新申报通知](https://www.suzhou.gov.cn/news/2026-notice)"
        ),
    ])
    client = TestClient(create_app(web_settings(), provider, web_search_tool=search_tool))

    response = client.post("/api/agent/chat", json=web_payload("今年创业社保补贴什么时候能申报？"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert "search_web" in {t["function"]["name"] for t in provider.tool_defs[0]}
    assert search_tool.queries == ["苏州创业社保补贴 2026 申报"]
    tool_messages = [message for message in provider.calls[1] if message.get("role") == "tool"]
    assert tool_messages and "2026-notice" in tool_messages[0]["content"]
    assert data["replyText"].startswith("根据苏州市政府官网")
    assert data["sources"] == [{
        "title": "苏州市创业社保补贴最新申报通知",
        "url": "https://www.suzhou.gov.cn/news/2026-notice",
    }]


def test_web_search_stream_done_event_carries_sources() -> None:
    search_tool = FakeWebSearchTool()
    provider = ScriptedToolProvider([
        ScriptedToolProvider.text("联网信息说明。"),
    ])
    client = TestClient(create_app(web_settings(), provider, web_search_tool=search_tool))

    response = client.post("/api/agent/chat/stream", json=web_payload("最近有什么新政策？"))

    assert response.status_code == 200
    events = [block.splitlines()[0][6:].strip() for block in response.text.strip().split("\n\n")]
    assert events == ["delta", "done"]


def test_web_search_unavailable_still_replies_without_sources() -> None:
    search_tool = FakeWebSearchTool(fail=True)
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("search_web", '{"query": "最新政策"}', "call-w1"),
        ScriptedToolProvider.text("联网搜索暂时不可用，以下基于本地已核验政策库回答。"),
    ])
    client = TestClient(create_app(web_settings(), provider, web_search_tool=search_tool))

    response = client.post("/api/agent/chat", json=web_payload("最近有什么新政策？"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["replyText"].startswith("联网搜索暂时不可用")
    assert data["sources"] == []


def test_web_search_toggle_without_server_key_returns_disabled_note() -> None:
    """服务端未配置 Key 时，开关打开也不注入真实工具，工具报 DISABLED。"""
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("search_web", '{"query": "最新政策"}', "call-w1"),
        ScriptedToolProvider.text("联网搜索服务未配置，以下基于本地已核验政策库回答。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=web_payload("最近有什么新政策？"))

    assert response.status_code == 200
    data = response.json()["data"]
    # 开关打开时工具对模型可见，但服务端未配置 Key，执行结果为 DISABLED。
    assert "search_web" in {t["function"]["name"] for t in provider.tool_defs[0]}
    tool_messages = [message for message in provider.calls[1] if message.get("role") == "tool"]
    assert tool_messages and "DISABLED" in tool_messages[0]["content"]
    assert data["replyText"].startswith("联网搜索服务未配置")
    assert data["sources"] == []


def test_search_web_tool_passes_model_time_range_and_defaults_recency_to_year() -> None:
    """模型传 time_range 时透传；近期类查询未指明年份时默认限定最近一年。"""

    class RecordingProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, str | None]] = []

        async def search(self, query: str, limit: int, time_range: str | None = None):
            self.calls.append((query, limit, time_range))
            return []

    provider = RecordingProvider()
    tool = WebSearchTool(provider, max_results=5)  # type: ignore[arg-type]

    asyncio.run(tool.search("最近有什么新政策", None))
    asyncio.run(tool.search("苏州创业社保补贴 2026 申报", None))
    asyncio.run(tool.search("苏州创业社保补贴申报条件", "month"))

    assert provider.calls == [
        ("最近有什么新政策", 5, "year"),
        ("苏州创业社保补贴 2026 申报", 5, None),
        ("苏州创业社保补贴申报条件", 5, "month"),
    ]


def test_tavily_provider_payload_carries_time_range() -> None:
    """time_range 必须真正进入 Tavily 请求体，作为时间定位约束。"""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"results": [
            {"title": "2026年新政策", "url": "https://www.suzhou.gov.cn/a", "content": "正文"},
        ]})

    provider = TavilyWebSearchProvider(
        api_key="test-key", timeout_seconds=1,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        results = asyncio.run(provider.search("苏州 新政策", 5, "year"))
    finally:
        asyncio.run(provider._client.aclose())  # type: ignore[attr-defined]

    assert captured["payload"]["time_range"] == "year"
    assert results and results[0].title == "2026年新政策"
