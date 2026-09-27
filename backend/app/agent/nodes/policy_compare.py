from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import PolicyCompareTool


class PolicyCompareNode:
    def __init__(self, tool: PolicyCompareTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.policyRelations = await self._tool.compare(state.candidatePolicies, state.eligibilityResults)
        state.stage = AgentStage.PLANNING
        return state
