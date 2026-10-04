from __future__ import annotations

import ipaddress
import logging
import re
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.realtime_policy.models import SearchResult

logger = logging.getLogger("uvicorn.error")

VALID_TIME_RANGES = ("day", "week", "month", "year")

# 查询带明确年份时不做时间范围偏置；带「最近/最新」等时效词且未指明年份时默认限定最近一年。
_RECENCY_PATTERN = re.compile(r"最近|最新|近期|今年|新政策|新政|目前|现在|刚刚|近来|今年")
_YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


class WebSearchProviderError(RuntimeError):
    pass


def safe_web_url(url: str) -> bool:
    """全网搜索仍保留传输层安全过滤：仅 HTTPS、无凭据、无私网/本地/回环地址。"""
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() != "https" or not host or parsed.username or parsed.password:
            return False
        if host == "localhost" or host.endswith(".localhost"):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True
        return not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        )
    except ValueError:
        return False


class TavilyWebSearchProvider:
    """Tavily 全网搜索 provider：与 realtime_policy 的政务域内检索不同，不限定域名。"""

    endpoint = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._client = client

    async def search(self, query: str, limit: int, time_range: str | None = None) -> list[SearchResult]:
        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": min(max(1, limit), 20),
            "include_published_date": True,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "language": "zh-cn",
            "safe_search": True,
        }
        # 时间范围约束：防止「最近/最新」类查询命中陈旧年份的网页。
        if time_range in VALID_TIME_RANGES:
            payload["time_range"] = time_range
        started = perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            response = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "web_search_provider_error provider=tavily duration_ms=%d error_type=timeout",
                (perf_counter() - started) * 1000,
            )
            raise TimeoutError("Web search timed out") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "web_search_provider_error provider=tavily duration_ms=%d error_type=network",
                (perf_counter() - started) * 1000,
            )
            raise WebSearchProviderError("Web search request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code >= 400:
            logger.warning(
                "web_search_provider_error provider=tavily status_code=%d duration_ms=%d error_type=http",
                response.status_code,
                (perf_counter() - started) * 1000,
            )
            raise WebSearchProviderError("Web search returned an HTTP error")

        try:
            body: Any = response.json()
        except ValueError as exc:
            raise WebSearchProviderError("Web search returned invalid JSON") from exc
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            raise WebSearchProviderError("Web search returned an invalid response schema")

        results: list[SearchResult] = []
        for item in body["results"]:
            normalized = self._normalize_item(item)
            if normalized is not None:
                results.append(normalized)
        return results[: max(1, limit)]

    @staticmethod
    def _normalize_item(item: Any) -> SearchResult | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(url, str) or not safe_web_url(url.strip()):
            return None
        content = item.get("content")
        return SearchResult(
            title=title.strip(),
            url=url.strip(),
            snippet=content.strip() if isinstance(content, str) else "",
            publishedAt=None,
        )


class WebSearchTool:
    """供 Agent 回复引擎调用的联网搜索工具；未配置时报告 DISABLED，不抛异常。"""

    def __init__(self, provider: TavilyWebSearchProvider, max_results: int) -> None:
        self._provider = provider
        self._max_results = max_results

    @staticmethod
    def _resolve_time_range(query: str, time_range: str | None) -> str | None:
        """近期类查询且未指明年份时，默认限定最近一年，避免命中去年旧文。"""
        if time_range:
            return time_range if time_range in VALID_TIME_RANGES else None
        if _YEAR_PATTERN.search(query):
            return None
        if _RECENCY_PATTERN.search(query):
            return "year"
        return None

    async def search(self, query: str, time_range: str | None = None) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {"status": "ERROR", "note": "缺少检索词", "results": []}
        effective_range = self._resolve_time_range(query, time_range)
        try:
            results = await self._provider.search(query, self._max_results, effective_range)
        except (TimeoutError, WebSearchProviderError) as exc:
            return {
                "status": "UNAVAILABLE",
                "note": f"联网搜索暂时不可用：{type(exc).__name__}；请基于已有信息回答",
                "results": [],
            }
        return {
            "status": "OK",
            "timeRange": effective_range,
            "results": [
                {
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                }
                for result in results
            ],
        }
