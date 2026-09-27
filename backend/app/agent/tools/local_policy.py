from __future__ import annotations

from app.agent.models import PolicyCandidate
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository


class LocalPolicySearchTool:
    """将本地未核验政策记录适配为既有 Agent 政策候选项。"""

    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

    @staticmethod
    def _topic(message: str) -> str | None:
        if "创业" in message:
            return "创业补贴"
        if "就业" in message or "求职" in message:
            return "就业补贴"
        if "社保" in message:
            return "社会保险"
        return None

    @staticmethod
    def _target_group(profile: UserProfile) -> str | None:
        if profile.graduationYear is not None:
            return "应届毕业生"
        if profile.employmentStatus == "创业中":
            return "创业者"
        return None

    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]:
        records = self._repository.filter(
            region=profile.city,
            topic=self._topic(message),
            target_group=self._target_group(profile),
        )
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
