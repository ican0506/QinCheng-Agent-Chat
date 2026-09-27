from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import EligibilityTool


class EligibilityNode:
    def __init__(self, tool: EligibilityTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.eligibilityResults = await self._tool.check(state.userProfile, state.candidatePolicies)
        state.stage = AgentStage.POLICY_COMPARING
        return state
