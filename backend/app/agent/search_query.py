"""按当前目标构造官方检索词；只影响联网查询，不改变结构化资格规则。"""
from __future__ import annotations

from datetime import date

from app.agent.models import GovernmentAgentState
from app.policy.repository import PolicyRepository
from app.services.policy_query_context import UserGoal


class AgentSearchQueryBuilder:
    def __init__(self, repository: PolicyRepository | None = None) -> None:
        self._repository = repository

    def build(self, state: GovernmentAgentState) -> str:
        if state.targetPolicyId and self._repository is not None:
            record = self._repository.get_by_id(state.targetPolicyId)
            if record is not None:
                return f"{record.region} {record.name} 官方办理信息"
        if state.userGoal is UserGoal.JOB_SEARCH:
            city = state.userProfile.city or "苏州"
            year = state.userProfile.graduationYear or date.today().year
            return f"{city} {year} 高校毕业生 招聘 就业服务 就业见习 官方招聘活动"
        return state.userMessage
