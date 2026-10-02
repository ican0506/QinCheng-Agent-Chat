from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.services.policy_query_context import (
    PolicyDomainIntent,
    PolicyDomainIntentDetector,
    PolicyQueryMode,
    PolicyQueryModeDetector,
)
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.material_check import MaterialCheckNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.nodes.realtime_policy_search import RealtimePolicySearchNode
from app.agent.tools.mock import MockEligibilityTool, MockPlanTool, MockPolicyCompareTool, MockPolicySearchTool
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.agent.tools.material_check import MaterialCheckTool
from app.agent.tools.base import PlanTool, PolicyCompareTool, PolicySearchTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from time import perf_counter


class WorkflowAgent:
    def __init__(self, profile_node: ProfileNode, policy_search_node: PolicySearchNode, eligibility_node: EligibilityNode, policy_compare_node: PolicyCompareNode, plan_node: PlanNode, material_check_node: MaterialCheckNode | None = None, realtime_node: RealtimePolicySearchNode | None = None) -> None:
        self._profile_node = profile_node
        self._policy_search_node = policy_search_node
        self._eligibility_node = eligibility_node
        self._policy_compare_node = policy_compare_node
        self._plan_node = plan_node
        self._material_check_node = material_check_node
        self._realtime_node = realtime_node

    @classmethod
    def default(cls, policy_search_tool: MockPolicySearchTool | None = None) -> WorkflowAgent:
        search_tool = policy_search_tool or MockPolicySearchTool()
        return cls(ProfileNode(), PolicySearchNode(search_tool), EligibilityNode(MockEligibilityTool()), PolicyCompareNode(MockPolicyCompareTool()), PlanNode(MockPlanTool()))

    @classmethod
    def production(
        cls,
        repository: PolicyRepository,
        policy_search_tool: PolicySearchTool,
        policy_compare_tool: PolicyCompareTool,
        plan_tool: PlanTool,
        realtime_node: RealtimePolicySearchNode | None = None,
    ) -> WorkflowAgent:
        return cls(
            ProfileNode(),
            PolicySearchNode(policy_search_tool),
            EligibilityNode(RuleEligibilityTool(repository)),
            PolicyCompareNode(policy_compare_tool),
            PlanNode(plan_tool),
            MaterialCheckNode(MaterialCheckTool(repository)),
            realtime_node,
        )

    async def run(self, session_id: str, message: str, user_profile: UserProfile, material_declarations: dict[str, bool] | None = None, policy_search_query: str | None = None, timings: dict[str, float] | None = None) -> GovernmentAgentState:
        state = GovernmentAgentState(
            sessionId=session_id,
            userMessage=message,
            userProfile=user_profile,
            materialDeclarations=material_declarations or {},
            policySearchQuery=policy_search_query,
            domainIntent=PolicyDomainIntentDetector.detect(message),
            queryMode=PolicyQueryModeDetector.detect(message),
        )
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            state.stage = AgentStage.COMPLETED
            return state
        state = await self._profile_node.execute(state)
        if state.needFollowUp:
            return state
        nodes = [self._policy_search_node]
        if self._realtime_node is not None:
            nodes.append(self._realtime_node)
        for node in nodes:
            node_started_at = perf_counter()
            state = await node.execute(state)
            if timings is not None and node is self._realtime_node:
                timings["realtime_search_ms"] = (perf_counter() - node_started_at) * 1000

        # 政策事实查询只返回政策与来源，不在画像不足时制造个性化资格结论。
        base_profile_complete = all(
            getattr(state.userProfile, field) not in (None, "")
            for field in ("city", "education", "graduationYear", "employmentStatus")
        )
        if state.queryMode is PolicyQueryMode.FACT_QUERY and not base_profile_complete:
            state.stage = AgentStage.COMPLETED
            return state

        nodes = [self._eligibility_node, self._policy_compare_node]
        if self._material_check_node is not None:
            nodes.append(self._material_check_node)
        nodes.append(self._plan_node)
        for node in nodes:
            node_started_at = perf_counter()
            state = await node.execute(state)
            if timings is not None and node is self._realtime_node:
                timings["realtime_search_ms"] = (perf_counter() - node_started_at) * 1000
        return state
