from __future__ import annotations

from app.agent.models import PolicyCandidate
from app.agent.tools.policy_intent import allows_policy_for_intent
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.rag.retriever import InMemoryRagRetriever
from app.services.policy_query_context import QueryTemporalIntent, QueryTemporalIntentDetector


class LocalPolicySearchTool:
    """将本地未核验政策记录适配为既有 Agent 政策候选项。"""

    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

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
        if "灵活就业" in message:
            return "就业"
        if "社会保险" in message or "社保" in message:
            return "社会保险"
        if "创业" in message:
            return "创业补贴"
        if "就业" in message or "求职" in message:
            return "就业"
        return None

    @staticmethod
    def _target_group(profile: UserProfile) -> str | None:
        if profile.graduationYear is not None:
            return "应届毕业生"
        if profile.employmentStatus == "创业中":
            return "创业者"
        return None

    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]:
        region = profile.city
        topic = self._topic(profile, message)
        target_group = self._target_group(profile)
        records = self._repository.filter(
            region=region,
            topic=topic,
            target_group=target_group,
        )
        if not records and target_group is not None:
            records = self._repository.filter(region=region, topic=topic)
        records = [record for record in records if allows_policy_for_intent(profile, record)]
        historical = QueryTemporalIntentDetector.detect(message) is QueryTemporalIntent.HISTORICAL
        records.sort(key=lambda record: (InMemoryRagRetriever.temporal_rank(record.validityStatus.value, record.applicationStatus.value, historical), record.policyId))
        return [
            PolicyCandidate(
                policyId=record.policyId,
                name=record.name,
                region=record.region,
                department=record.department,
                summary=record.summary,
                effectiveDate=record.effectiveDate or "",
                expiryDate=record.expiryDate,
                sourceUrl=record.sourceUrl or "",
                matchReason="基于本地未核验政策数据的地区、主题和目标群体筛选结果。",
                conditions=[condition.description for condition in record.conditions],
                requiredMaterials=record.requiredMaterials,
                process=record.process,
                isMock=False,
            )
            for record in records
        ]
