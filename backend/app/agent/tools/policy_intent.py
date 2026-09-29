from __future__ import annotations

from collections.abc import Iterable

from app.models.chat import UserProfile
from app.policy.models import PolicyRecord


def allows_policy_for_intent(profile: UserProfile, policy: PolicyRecord) -> bool:
    """只根据政策结构化主题排除与用户明确否定的创业方向冲突的候选。"""
    return not (
        profile.entrepreneurshipIntent is False
        and "创业补贴" in policy.topics
    )


def allowed_policy_ids(profile: UserProfile, policies: Iterable[PolicyRecord]) -> set[str]:
    return {
        policy.policyId
        for policy in policies
        if allows_policy_for_intent(profile, policy)
    }
