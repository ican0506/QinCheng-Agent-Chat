"""兼容旧调用面的 WorkflowAgent；实际编排交由 LangGraph。"""
from __future__ import annotations

from app.agent.graph import GovernmentAgentGraph
from app.agent.graph.nodes import GraphNodeAdapter
from app.agent.models import GovernmentAgentState
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.material_check import MaterialCheckNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.nodes.realtime_policy_search import RealtimePolicySearchNode
from app.agent.tools.base import PlanTool, PolicyCompareTool, PolicySearchTool
from app.agent.tools.material_check import MaterialCheckTool
from app.agent.tools.mock import (
    MockEligibilityTool,
    MockPlanTool,
    MockPolicyCompareTool,
    MockPolicySearchTool,
)
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.services.policy_query_context import (
    PolicyDomainIntentDetector,
    PolicyQueryModeDetector,
    UserGoal,
)


class WorkflowAgent:
    """Graph 的兼容外观，保留既有构造器与 ``run`` 接口。"""

    def __init__(
        self,
        profile_node: ProfileNode,
        policy_search_node: PolicySearchNode,
        eligibility_node: EligibilityNode,
        policy_compare_node: PolicyCompareNode,
        plan_node: PlanNode,
        material_check_node: MaterialCheckNode | None = None,
        realtime_node: RealtimePolicySearchNode | None = None,
        repository: PolicyRepository | None = None,
    ) -> None:
        # 保留旧测试和依赖注入的可观测入口；图适配器使用同一批实例。
        self._profile_node = profile_node
        self._policy_search_node = policy_search_node
        self._eligibility_node = eligibility_node
        self._policy_compare_node = policy_compare_node
        self._plan_node = plan_node
        self._material_check_node = material_check_node
        self._realtime_node = realtime_node
        self._graph = GovernmentAgentGraph(
            GraphNodeAdapter(
                profile=self._profile_node,
                policy_search=self._policy_search_node,
                eligibility=self._eligibility_node,
                policy_compare=self._policy_compare_node,
                material=self._material_check_node,
                plan=self._plan_node,
                realtime=self._realtime_node,
                repository=repository,
            )
        )

    @classmethod
    def default(cls, policy_search_tool: MockPolicySearchTool | None = None) -> "WorkflowAgent":
        search_tool = policy_search_tool or MockPolicySearchTool()
        return cls(
            ProfileNode(),
            PolicySearchNode(search_tool),
            EligibilityNode(MockEligibilityTool()),
            PolicyCompareNode(MockPolicyCompareTool()),
            PlanNode(MockPlanTool()),
        )

    @classmethod
    def production(
        cls,
        repository: PolicyRepository,
        policy_search_tool: PolicySearchTool,
        policy_compare_tool: PolicyCompareTool,
        plan_tool: PlanTool,
        realtime_node: RealtimePolicySearchNode | None = None,
    ) -> "WorkflowAgent":
        return cls(
            ProfileNode(),
            PolicySearchNode(policy_search_tool, repository),
            EligibilityNode(RuleEligibilityTool(repository)),
            PolicyCompareNode(policy_compare_tool),
            PlanNode(plan_tool),
            MaterialCheckNode(MaterialCheckTool(repository)),
            realtime_node,
            repository,
        )

    async def run(
        self,
        session_id: str,
        message: str,
        user_profile: UserProfile,
        material_declarations: dict[str, bool] | None = None,
        policy_search_query: str | None = None,
        timings: dict[str, float] | None = None,
        user_goal: UserGoal | None = None,
        active_goal: UserGoal | None = None,
    ) -> GovernmentAgentState:
        state = GovernmentAgentState(
            sessionId=session_id,
            userMessage=message,
            userProfile=user_profile,
            materialDeclarations=material_declarations or {},
            policySearchQuery=policy_search_query,
            domainIntent=PolicyDomainIntentDetector.detect(message),
            queryMode=PolicyQueryModeDetector.detect(message),
            userGoal=user_goal or UserGoal.POLICY_DISCOVERY,
            requestedGoal=user_goal,
            activeGoal=active_goal,
            messages=[{"role": "user", "content": message}],
        )
        state = await self._graph.ainvoke(state)
        if timings is not None:
            timings["realtime_search_ms"] = state.realtimeSearchMs
        return state
