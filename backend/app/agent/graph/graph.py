"""GovernmentAgent 的 LangGraph 编排定义。"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.graph.nodes import GraphNodeAdapter
from app.agent.graph.state import GovernmentAgentGraphState
from app.agent.models import EligibilityStatus, GovernmentAgentState
from app.realtime_policy.intent import FreshnessIntentDetector
from app.services.policy_query_context import UserGoal


class GovernmentAgentGraph:
    """按 RouteDecision 编排既有节点的异步 StateGraph。"""

    def __init__(self, nodes: GraphNodeAdapter) -> None:
        self._nodes = nodes
        graph = StateGraph(GovernmentAgentGraphState)
        graph.add_node("resolve_goal", self._resolve_goal)
        graph.add_node("merge_profile", self._merge_profile)
        graph.add_node("official_search", self._official_search)
        graph.add_node("policy_search", self._policy_search)
        graph.add_node("required_fields", self._required_fields)
        graph.add_node("eligibility", self._eligibility)
        graph.add_node("policy_compare", self._policy_compare)
        graph.add_node("material", self._material)
        graph.add_node("plan", self._plan)
        graph.add_node("presentation", self._presentation)
        graph.add_edge(START, "resolve_goal")
        graph.add_conditional_edges(
            "resolve_goal",
            self._after_goal_resolution,
            {"merge_profile": "merge_profile", "presentation": "presentation"},
        )
        graph.add_conditional_edges(
            "merge_profile",
            self._route_goal,
            {
                "official": "official_search",
                "policy": "policy_search",
                "presentation": "presentation",
            },
        )
        graph.add_edge("official_search", "policy_search")
        graph.add_conditional_edges(
            "policy_search",
            self._after_policy_search,
            {"required_fields": "required_fields", "material": "material", "presentation": "presentation"},
        )
        graph.add_edge("required_fields", "eligibility")
        graph.add_conditional_edges(
            "eligibility",
            self._after_eligibility,
            {"policy_compare": "policy_compare", "presentation": "presentation"},
        )
        graph.add_edge("policy_compare", "material")
        graph.add_edge("material", "plan")
        graph.add_edge("plan", "presentation")
        graph.add_edge("presentation", END)
        self._graph = graph.compile()

    async def ainvoke(self, state: GovernmentAgentState) -> GovernmentAgentState:
        result = await self._graph.ainvoke({"agent": state})
        return result["agent"]

    async def _resolve_goal(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.resolve_goal(data["agent"])}

    async def _merge_profile(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.merge_profile(data["agent"])}

    async def _official_search(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.official_search(data["agent"])}

    async def _policy_search(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.policy_search(data["agent"])}

    async def _required_fields(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.required_fields(data["agent"])}

    async def _eligibility(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.eligibility(data["agent"])}

    async def _policy_compare(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.policy_compare(data["agent"])}

    async def _material(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.material(data["agent"])}

    async def _plan(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.plan(data["agent"])}

    async def _presentation(self, data: GovernmentAgentGraphState) -> GovernmentAgentGraphState:
        return {"agent": await self._nodes.presentation(data["agent"])}

    @staticmethod
    def _after_goal_resolution(data: GovernmentAgentGraphState) -> str:
        return (
            "presentation"
            if data["agent"].userGoal in {UserGoal.OUT_OF_SCOPE, UserGoal.CONVERSATIONAL}
            else "merge_profile"
        )

    @staticmethod
    def _route_goal(data: GovernmentAgentGraphState) -> str:
        state = data["agent"]
        if not state.routeDecision.runPolicySearch:
            return "presentation"
        if state.userGoal in {UserGoal.POLICY_FACT, UserGoal.POLICY_DISCOVERY, UserGoal.JOB_SEARCH}:
            return "official"
        if FreshnessIntentDetector.detect(state.userMessage).requiresRealtimeSearch:
            return "official"
        return "policy"

    @staticmethod
    def _after_policy_search(data: GovernmentAgentGraphState) -> str:
        state = data["agent"]
        if state.routeDecision.runEligibility:
            return "required_fields"
        if state.routeDecision.runMaterialCheck:
            return "material"
        return "presentation"

    @staticmethod
    def _after_eligibility(data: GovernmentAgentGraphState) -> str:
        state = data["agent"]
        if state.routeDecision.runMaterialCheck and any(
            result.overallStatus is EligibilityStatus.PASS for result in state.eligibilityResults
        ):
            return "policy_compare"
        return "presentation"
