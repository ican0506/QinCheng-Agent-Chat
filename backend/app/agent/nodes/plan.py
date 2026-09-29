from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import PlanTool


class PlanNode:
    def __init__(self, tool: PlanTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        state.overallPlan = await self._tool.build_plan(
            state.userProfile,
            state.candidatePolicies,
            state.eligibilityResults,
            state.policyRelations,
            state.materialResults,
        )
        state.stage = AgentStage.COMPLETED
        state.nextAction = (
            "请先补充关键画像信息后重新核验资格。"
            if state.needFollowUp
            else "查看基于当前政策资格、时效和申报窗口生成的办理路径。"
        )
        return state
