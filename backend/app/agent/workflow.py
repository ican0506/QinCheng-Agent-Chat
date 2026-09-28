from __future__ import annotations

from app.agent.models import GovernmentAgentState
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.tools.mock import MockEligibilityTool, MockPlanTool, MockPolicyCompareTool, MockPolicySearchTool
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.agent.tools.base import PlanTool, PolicyCompareTool, PolicySearchTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository


class WorkflowAgent:
    def __init__(self, profile_node: ProfileNode, policy_search_node: PolicySearchNode, eligibility_node: EligibilityNode, policy_compare_node: PolicyCompareNode, plan_node: PlanNode) -> None:
        self._profile_node = profile_node
        self._policy_search_node = policy_search_node
        self._eligibility_node = eligibility_node
        self._policy_compare_node = policy_compare_node
        self._plan_node = plan_node

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
    ) -> WorkflowAgent:
        return cls(
            ProfileNode(),
            PolicySearchNode(policy_search_tool),
            EligibilityNode(RuleEligibilityTool(repository)),
            PolicyCompareNode(policy_compare_tool),
            PlanNode(plan_tool),
        )

    async def run(self, session_id: str, message: str, user_profile: UserProfile) -> GovernmentAgentState:
        state = GovernmentAgentState(sessionId=session_id, userMessage=message, userProfile=user_profile)
        state = await self._profile_node.execute(state)
        if state.needFollowUp:
            return state
        for node in (self._policy_search_node, self._eligibility_node, self._policy_compare_node, self._plan_node):
            state = await node.execute(state)
        return state
