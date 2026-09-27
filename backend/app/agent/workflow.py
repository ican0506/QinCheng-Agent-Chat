from __future__ import annotations

from app.agent.models import GovernmentAgentState
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.tools.mock import MockEligibilityTool, MockPlanTool, MockPolicyCompareTool, MockPolicySearchTool
from app.models.chat import UserProfile


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

    async def run(self, session_id: str, message: str, user_profile: UserProfile) -> GovernmentAgentState:
        state = GovernmentAgentState(sessionId=session_id, userMessage=message, userProfile=user_profile)
        state = await self._profile_node.execute(state)
        if state.needFollowUp:
            return state
        for node in (self._policy_search_node, self._eligibility_node, self._policy_compare_node, self._plan_node):
            state = await node.execute(state)
        return state
