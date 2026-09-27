from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import PlanTool


class PlanNode:
    def __init__(self, tool: PlanTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.overallPlan = await self._tool.build_plan(state.candidatePolicies, state.eligibilityResults, state.policyRelations)
        state.stage = AgentStage.COMPLETED
        state.nextAction = "查看 Demo 办理计划，并以当地官方政策为准。"
        return state
