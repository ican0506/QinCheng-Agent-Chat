from __future__ import annotations

from datetime import date, datetime
from email.utils import parsedate_to_datetime
import logging
from time import perf_counter
from typing import Any

import httpx

from app.realtime_policy.models import SearchResult


logger = logging.getLogger("uvicorn.error")


class TavilyProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TavilyRealtimeSearchProvider:
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

    async def search(
        self,
        query: str,
        allowed_domains: list[str],
        limit: int,
    ) -> list[SearchResult]:
        domains = [domain.strip().lower() for domain in allowed_domains if domain.strip()]
        if not domains:
            raise TavilyProviderError("Tavily search requires at least one allowed domain")

        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": min(max(1, limit), 20),
            "include_domains": domains,
            "include_domains_mode": "restrict",
            "include_published_date": True,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "language": "zh-cn",
            "filter_by_language": False,
            "auto_parameters": False,
            "safe_search": True,
        }
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
                "realtime_provider_error provider=tavily status_code=none duration_ms=%d error_type=timeout",
                (perf_counter() - started) * 1000,
            )
            raise TimeoutError("Tavily search timed out") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "realtime_provider_error provider=tavily status_code=none duration_ms=%d error_type=network",
                (perf_counter() - started) * 1000,
            )
            raise TavilyProviderError("Tavily search request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code >= 400:
            logger.warning(
                "realtime_provider_error provider=tavily status_code=%d duration_ms=%d error_type=http",
                response.status_code,
                (perf_counter() - started) * 1000,
            )
            raise TavilyProviderError(
                "Tavily search returned an HTTP error",
                status_code=response.status_code,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise TavilyProviderError("Tavily search returned invalid JSON") from exc
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            raise TavilyProviderError("Tavily search returned an invalid response schema")

        results: list[SearchResult] = []
        for item in body["results"]:
            normalized = self._normalize_item(item)
            if normalized is not None:
                results.append(normalized)
        return results[:limit]

    @classmethod
    def _normalize_item(cls, item: Any) -> SearchResult | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(url, str) or not url.strip():
            return None
        content = item.get("content")
        return SearchResult(
            title=title.strip(),
            url=url.strip(),
            snippet=content.strip() if isinstance(content, str) else "",
            publishedAt=cls._parse_published_date(item.get("published_date")),
        )

    @staticmethod
    def _parse_published_date(value: Any) -> date | None:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        try:
            return parsedate_to_datetime(text).date()
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            return None
