import asyncio
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.realtime_policy.models import RealtimePolicyHit, RealtimeSearchStatus
from app.realtime_policy.provider import RealtimeSearchProvider, DisabledRealtimeSearchProvider
from app.realtime_policy.query import build_query
from app.realtime_policy.security import canonical_url


def normalized_name(name: str) -> str:
    return re.sub(r'[\s（）()《》：:、，,。]', '', name)


class OfficialRealtimePolicySearchTool:
    def __init__(self, provider: RealtimeSearchProvider, repository: PolicyRepository, allowed_domains: list[str], *, timeout_seconds: float = 8, max_results: int = 5):
        self.provider = provider
        self.repository = repository
        self.allowed_domains = allowed_domains
        self.timeout_seconds = timeout_seconds
        self.max_results = max_results

    async def search(self, profile: UserProfile, message: str, reason: str) -> tuple[RealtimeSearchStatus, list[RealtimePolicyHit]]:
        if isinstance(self.provider, DisabledRealtimeSearchProvider):
            return RealtimeSearchStatus.DISABLED, []
        query, keywords = build_query(message, profile, [r.name for r in self.repository.filter()])
        try:
            results = await asyncio.wait_for(self.provider.search(query, list(self.allowed_domains), self.max_results), timeout=self.timeout_seconds)
            hits = []
            seen = set()
            for result in results:
                url = canonical_url(result.url, self.allowed_domains)
                if not url or url in seen:
                    continue
                seen.add(url)
                related = self._related_id(url, result.title)
                hits.append(RealtimePolicyHit(hitId=hashlib.sha256(url.encode()).hexdigest()[:16], title=result.title, url=url, snippet=result.snippet, publishedAt=result.publishedAt, domain=urlsplit(url).hostname, retrievedAt=datetime.now(timezone.utc), matchedKeywords=[k for k in keywords if k in result.title or k in result.snippet], relatedPolicyId=related, freshnessReason=reason))
            hits.sort(key=lambda h: (-len(h.matchedKeywords), -(h.publishedAt.toordinal() if h.publishedAt else 0), h.relatedPolicyId is None, h.url))
            return (RealtimeSearchStatus.SUCCESS if hits else RealtimeSearchStatus.NO_RESULTS), hits[:self.max_results]
        except TimeoutError:
            return RealtimeSearchStatus.TIMEOUT, []
        except Exception:
            return RealtimeSearchStatus.ERROR, []

    def _related_id(self, url: str, title: str) -> str | None:
        records = self.repository.filter()
        exact = [r.policyId for r in records if r.sourceUrl and canonical_url(r.sourceUrl, self.allowed_domains) == url]
        if len(exact) == 1:
            return exact[0]
        title_name = normalized_name(title)
        names = [r.policyId for r in records if normalized_name(r.name) == title_name]
        return names[0] if len(names) == 1 else None
