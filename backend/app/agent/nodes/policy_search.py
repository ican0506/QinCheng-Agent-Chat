from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.goal_policy_ranking import GoalAwarePolicyRanker
from app.agent.tools.base import PolicySearchTool
from app.policy.repository import PolicyRepository


class PolicySearchNode:
    def __init__(self, tool: PolicySearchTool, repository: PolicyRepository | None = None) -> None:
        self._tool = tool
        self._ranker = GoalAwarePolicyRanker(repository)

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        query = state.policySearchQuery or state.userMessage
        search_outcome = getattr(self._tool, "search_outcome", None)
        if callable(search_outcome):
            outcome = await search_outcome(state.userProfile, query)
            state.candidatePolicies = outcome.structuredCandidates
            state.knowledgeEvidences = outcome.knowledgeEvidences
        else:
            state.candidatePolicies = await self._tool.search(state.userProfile, query)
        state.candidatePolicies = self._ranker.rank(state.userGoal, state.candidatePolicies)
        state.activePolicy = (
            state.candidatePolicies[0].policyId if state.candidatePolicies else None
        )
        state.stage = AgentStage.ELIGIBILITY_CHECKING
        return state
