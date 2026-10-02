from __future__ import annotations

from collections.abc import Iterable

from app.models.chat import UserProfile
from app.policy.models import PolicyRecord


def allows_policy_for_intent(profile: UserProfile, policy: PolicyRecord) -> bool:
    """只根据明确用户意图与结构化元数据排除冲突候选。"""
    if profile.entrepreneurshipIntent is False and "创业补贴" in policy.topics:
        return False

    is_pure_flexible_employment = (
        "灵活就业" in policy.name
        or any("灵活就业" in value for value in policy.topics)
        or any("灵活就业" in value for value in policy.targetGroups)
    )
    if is_pure_flexible_employment and (
        profile.flexibleEmploymentInsurance is False
        or (
            profile.entrepreneurshipIntent is True
            and profile.flexibleEmploymentInsurance is not True
        )
    ):
        return False
    return True


def allowed_policy_ids(profile: UserProfile, policies: Iterable[PolicyRecord]) -> set[str]:
    return {
        policy.policyId
        for policy in policies
        if allows_policy_for_intent(profile, policy)
    }
