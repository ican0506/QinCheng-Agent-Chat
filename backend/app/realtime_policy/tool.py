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
from app.services.policy_query_context import QueryTemporalIntent, QueryTemporalIntentDetector


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
            if QueryTemporalIntentDetector.detect(message) is QueryTemporalIntent.HISTORICAL:
                hits.sort(key=lambda hit: self._historical_rank(hit, message))
            else:
                hits.sort(key=lambda h: (-len(h.matchedKeywords), -(h.publishedAt.toordinal() if h.publishedAt else 0), h.relatedPolicyId is None, h.url))
            return (RealtimeSearchStatus.SUCCESS if hits else RealtimeSearchStatus.NO_RESULTS), hits[:self.max_results]
        except TimeoutError:
            return RealtimeSearchStatus.TIMEOUT, []
        except Exception:
            return RealtimeSearchStatus.ERROR, []

    def _historical_rank(self, hit: RealtimePolicyHit, message: str) -> tuple:
        """历史查询优先精确届别的正式申报通知；冲突届别仅降权、不删除。"""
        target_match = re.search(r"(20\d{2})(?:届|年)", message)
        target_year = target_match.group(1) if target_match else None
        hit_years = set(re.findall(r"20\d{2}", f"{hit.title} {hit.snippet}"))
        target_year_match = bool(target_year and target_year in hit_years)
        conflicting_year = bool(target_year and hit_years and target_year not in hit_years)
        topic_match = "求职创业补贴" in message and "求职创业补贴" in f"{hit.title} {hit.snippet}"
        formal_notice = bool(re.search(r"申报|申领|申请|通知|截止", f"{hit.title} {hit.snippet}"))
        weak_page = bool(re.search(r"栏目|分享|攻略|新闻|动态", hit.title))
        related_exact = False
        if hit.relatedPolicyId:
            record = self.repository.get_by_id(hit.relatedPolicyId)
            if record is not None:
                record_text = " ".join([record.name, *record.topics, *record.applicableCohorts])
                related_exact = bool(
                    (not target_year or target_year in record_text)
                    and ("求职创业补贴" not in message or "求职创业补贴" in record_text)
                )
        published = hit.publishedAt.toordinal() if hit.publishedAt else 0
        return (
            int(conflicting_year),
            -int(related_exact),
            -int(target_year_match and topic_match and formal_notice),
            -int(topic_match and formal_notice),
            -int(topic_match),
            -int(target_year_match),
            int(weak_page),
            -len(hit.matchedKeywords),
            -published,
            hit.url,
        )

    def _related_id(self, url: str, title: str) -> str | None:
        records = self.repository.filter()
        exact = [r.policyId for r in records if r.sourceUrl and canonical_url(r.sourceUrl, self.allowed_domains) == url]
        if len(exact) == 1:
            return exact[0]
        title_name = normalized_name(title)
        names = [r.policyId for r in records if normalized_name(r.name) == title_name]
        return names[0] if len(names) == 1 else None
