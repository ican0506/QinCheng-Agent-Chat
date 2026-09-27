from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import PolicySearchTool


class PolicySearchNode:
    def __init__(self, tool: PolicySearchTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.candidatePolicies = await self._tool.search(state.userProfile, state.userMessage)
        state.stage = AgentStage.ELIGIBILITY_CHECKING
        return state
