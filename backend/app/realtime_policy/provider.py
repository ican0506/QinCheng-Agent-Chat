import asyncio
from typing import Protocol
from app.realtime_policy.models import SearchResult


class RealtimeSearchProvider(Protocol):
    async def search(self, query: str, allowed_domains: list[str], limit: int) -> list[SearchResult]: ...


class DisabledRealtimeSearchProvider:
    async def search(self, query: str, allowed_domains: list[str], limit: int) -> list[SearchResult]:
        raise RuntimeError('未配置实时检索服务')


class FakeRealtimeSearchProvider:
    """测试注入用；不用于默认应用配置。"""
    def __init__(self, results: list[SearchResult], *, error: Exception | None = None, delay: float = 0):
        self.results = results
        self.error = error
        self.delay = delay
        self.call_count = 0
        self.calls: list[tuple[str, list[str], int]] = []

    async def search(self, query: str, allowed_domains: list[str], limit: int) -> list[SearchResult]:
        self.call_count += 1
        self.calls.append((query, list(allowed_domains), limit))
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.results[:limit]
