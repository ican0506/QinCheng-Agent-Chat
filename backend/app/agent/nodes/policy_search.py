from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import PolicySearchTool


class PolicySearchNode:
    def __init__(self, tool: PolicySearchTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        query = state.policySearchQuery or state.userMessage
        search_outcome = getattr(self._tool, "search_outcome", None)
        if callable(search_outcome):
            outcome = await search_outcome(state.userProfile, query)
            state.candidatePolicies = outcome.structuredCandidates
            state.knowledgeEvidences = outcome.knowledgeEvidences
        else:
            state.candidatePolicies = await self._tool.search(state.userProfile, query)
        state.stage = AgentStage.ELIGIBILITY_CHECKING
        return state
