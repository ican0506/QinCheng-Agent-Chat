from __future__ import annotations

from app.agent.models import EligibilityResult, PolicyCandidate, PolicyRelation
from app.policy.relations import PolicyRelationRepository
from app.policy.repository import PolicyRepository


class DeterministicPolicyCompareTool:
    """仅基于显式、已核验关系配置输出政策关系。"""

    def __init__(self, repository: PolicyRepository, relation_repository: PolicyRelationRepository) -> None:
        self._repository = repository
        self._relation_repository = relation_repository

    async def compare(
        self, policies: list[PolicyCandidate], eligibility: list[EligibilityResult]
    ) -> list[PolicyRelation]:
        candidate_ids = {policy.policyId for policy in policies}
        seen: set[tuple[str, str, str]] = set()
        relations: list[PolicyRelation] = []
        for item in self._relation_repository.all():
            key = (item.sourcePolicyId, item.targetPolicyId, item.relationType.value)
            if item.sourcePolicyId == item.targetPolicyId or key in seen:
                continue
            if item.sourcePolicyId not in candidate_ids or item.targetPolicyId not in candidate_ids:
                continue
            if self._repository.get_by_id(item.sourcePolicyId) is None or self._repository.get_by_id(item.targetPolicyId) is None:
                continue
            seen.add(key)
            relations.append(PolicyRelation(
                fromPolicyId=item.sourcePolicyId,
                toPolicyId=item.targetPolicyId,
                relationType=item.relationType,
                reason=item.reason,
                policyEvidence=item.policyEvidence,
            ))
        return sorted(relations, key=lambda item: (item.fromPolicyId, item.toPolicyId, item.relationType.value))
