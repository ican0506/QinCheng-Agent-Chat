"""按已解析目标与结构化政策元数据排序，不重新检索也不判断资格。"""
from __future__ import annotations

from app.agent.models import PolicyCandidate
from app.policy.repository import PolicyRepository
from app.services.policy_query_context import UserGoal


class GoalAwarePolicyRanker:
    def __init__(self, repository: PolicyRepository | None = None) -> None:
        self._repository = repository

    def rank(self, goal: UserGoal, candidates: list[PolicyCandidate]) -> list[PolicyCandidate]:
        if self._repository is None or goal not in {UserGoal.JOB_SEARCH, UserGoal.POLICY_DISCOVERY}:
            return candidates

        def score(candidate: PolicyCandidate) -> int:
            record = self._repository.get_by_id(candidate.policyId)
            if record is None:
                return 0
            topics = set(record.topics)
            if goal is UserGoal.JOB_SEARCH:
                # 仅依赖 PolicyRecord 的主题元数据：找工作优先见习和就业支持，
                # 不将创业类政策作为默认首选。
                return (
                    80 * int("就业见习" in topics)
                    + 40 * int("就业" in topics)
                    - 70 * int("创业补贴" in topics)
                )
            return 20 * int("就业" in topics) + 10 * int("创业补贴" in topics)

        ranked = [
            candidate
            for _, candidate in sorted(
                enumerate(candidates),
                key=lambda item: (-score(item[1]), item[0]),
            )
        ]
        # 找工作时创业政策不是默认推荐。保留“全为空”的兜底，避免未来政策库
        # 尚未覆盖就业服务时直接把正常结果清空。
        if goal is UserGoal.JOB_SEARCH:
            non_startup = [candidate for candidate in ranked if not self._is_startup(candidate)]
            return non_startup or ranked
        return ranked

    def _is_startup(self, candidate: PolicyCandidate) -> bool:
        record = self._repository.get_by_id(candidate.policyId) if self._repository else None
        return bool(record and "创业补贴" in set(record.topics))
