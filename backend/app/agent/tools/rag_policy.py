from __future__ import annotations

import re

from app.agent.models import PolicyCandidate
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.policy_intent import allowed_policy_ids
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.rag.models import RagSearchHit
from app.rag.retriever import InMemoryRagRetriever


class RagPolicySearchTool:
    """基于已核验本地政策原文进行召回，并在异常时回退到本地结构化筛选。"""

    def __init__(
        self,
        retriever: InMemoryRagRetriever | None,
        repository: PolicyRepository,
        fallback: LocalPolicySearchTool,
    ) -> None:
        self._retriever = retriever
        self._repository = repository
        self._fallback = fallback

    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]:
        try:
            hits = self.search_with_evidence(profile, message)
        except Exception:
            return await self._fallback.search(profile, message)
        return self._candidates_from_hits(hits)

    def search_with_evidence(self, profile: UserProfile, message: str) -> list[RagSearchHit]:
        if self._retriever is None:
            raise RuntimeError("本地政策原文索引不可用")
        policy_ids = allowed_policy_ids(profile, self._repository.filter())
        if not policy_ids:
            return []
        return self._retriever.search(
            message,
            region=profile.city,
            topic=self._topic(profile, message),
            target_group=self._target_group(profile, message),
            policy_ids=policy_ids,
            include_historical=self._asks_for_historical_record(message),
            top_k=8,
        )

    @staticmethod
    def _topic(profile: UserProfile, message: str) -> str | None:
        if profile.entrepreneurshipIntent is False:
            if "灵活就业" in message or "社保" in message or "社会保险" in message:
                return "社会保险"
            if profile.jobSeekingIntent:
                return "就业"
            return None
        if "求职创业补贴" in message:
            return "求职创业补贴"
        if "就业见习" in message:
            return "就业见习"
        if "灵活就业" in message or "社保" in message or "社会保险" in message:
            return "社会保险"
        if "创业" in message:
            return "创业补贴"
        if "就业" in message or "求职" in message:
            return "就业"
        return None

    @staticmethod
    def _target_group(profile: UserProfile, message: str) -> str | None:
        if "应届" in message:
            return "应届毕业生"
        return None

    @staticmethod
    def _asks_for_historical_record(message: str) -> bool:
        return bool(re.search(r"历史|往年|20\d{2}|\d{4}届", message))

    def _candidates_from_hits(self, hits: list[RagSearchHit]) -> list[PolicyCandidate]:
        candidates: list[PolicyCandidate] = []
        seen_policy_ids: set[str] = set()
        for hit in hits:
            if hit.policyId in seen_policy_ids:
                continue
            record = self._repository.get_by_id(hit.policyId)
            if record is None:
                continue
            seen_policy_ids.add(hit.policyId)
            snippet = " ".join(hit.chunkText.split())[:160]
            candidates.append(PolicyCandidate(
                policyId=record.policyId,
                name=record.name,
                region=record.region,
                department=record.department,
                summary=record.summary,
                effectiveDate=record.effectiveDate or "",
                expiryDate=record.expiryDate,
                sourceUrl=record.sourceUrl or hit.sourceUrl,
                matchReason=f"RAG 命中「{hit.heading}」原文片段（相关度 {hit.score:.2f}）：{snippet}",
                conditions=[condition.description for condition in record.conditions],
                requiredMaterials=record.requiredMaterials,
                process=record.process,
                isMock=False,
            ))
        return candidates
