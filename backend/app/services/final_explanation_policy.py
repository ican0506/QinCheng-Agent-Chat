from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.agent.models import GovernmentAgentState
from app.realtime_policy.models import RealtimeSearchStatus
from app.services.policy_query_context import PolicyDomainIntent


class FinalExplanationSkipReason(str, Enum):
    NONE = "NONE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    FOLLOW_UP = "FOLLOW_UP"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"
    NO_POLICY = "NO_POLICY"
    MATERIAL_UPDATE = "MATERIAL_UPDATE"
    REALTIME_STATUS_ONLY = "REALTIME_STATUS_ONLY"


@dataclass(frozen=True)
class FinalExplanationDecision:
    generate: bool
    skip_reason: FinalExplanationSkipReason = FinalExplanationSkipReason.NONE


class FinalExplanationPolicy:
    """只根据结构化状态决定是否值得等待最终解释模型。"""

    @staticmethod
    def decide(
        state: GovernmentAgentState, *, material_updated: bool = False
    ) -> FinalExplanationDecision:
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            return FinalExplanationDecision(False, FinalExplanationSkipReason.OUT_OF_SCOPE)
        if material_updated:
            return FinalExplanationDecision(False, FinalExplanationSkipReason.MATERIAL_UPDATE)
        if state.candidatePolicies and all(
            policy.policyId in state.policyReferenceNotices
            for policy in state.candidatePolicies
        ):
            return FinalExplanationDecision(False, FinalExplanationSkipReason.HISTORICAL_ONLY)
        if state.needFollowUp and state.followUpQuestions:
            return FinalExplanationDecision(False, FinalExplanationSkipReason.FOLLOW_UP)
        if (
            state.realtimeSearchStatus is not RealtimeSearchStatus.NOT_TRIGGERED
            and not state.candidatePolicies
            and len(state.realtimePolicyHits) <= 1
        ):
            return FinalExplanationDecision(False, FinalExplanationSkipReason.REALTIME_STATUS_ONLY)
        if not state.candidatePolicies and not state.realtimePolicyHits:
            return FinalExplanationDecision(False, FinalExplanationSkipReason.NO_POLICY)
        return FinalExplanationDecision(True)
