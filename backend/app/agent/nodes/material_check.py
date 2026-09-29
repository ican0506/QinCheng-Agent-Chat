from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.material_check import MaterialCheckTool


class MaterialCheckNode:
    def __init__(self, tool: MaterialCheckTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.materialResults, state.materialDeclarations = await self._tool.check(
            state.userMessage, state.candidatePolicies, state.materialDeclarations
        )
        state.stage = AgentStage.PLANNING
        return state
