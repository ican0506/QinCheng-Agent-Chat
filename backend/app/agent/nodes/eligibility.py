from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.agent.tools.base import EligibilityTool
from app.services.policy_query_context import UserGoal


class EligibilityNode:
    _questions = {
        "graduationDate": "请提供您的毕业日期，以便准确核验毕业年限。",
        "socialInsuranceMonths": "请问您连续缴纳社会保险已有几个月？",
        "businessRegistrationMonths": "请问您的经营主体登记注册已有几个月？",
        "residencyRegistration": "请问您是否具有本市户籍？",
        "unemploymentStatus": "请问您当前是否处于未就业状态？",
        "flexibleEmploymentInsurance": "请问您是否已按灵活就业方式参保并缴费？",
        "jobSeekingIntent": "请确认您是否有就业或创业意愿。",
        "hardshipIdentity": "请问您是否属于政策列明的困难毕业生身份？",
    }

    def __init__(self, tool: EligibilityTool) -> None:
        self._tool = tool

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        if not state.routeDecision.runEligibility:
            state.stage = AgentStage.COMPLETED
            return state
        state.eligibilityResults = await self._tool.check(state.userProfile, state.candidatePolicies)
        missing_fields = list(dict.fromkeys(
            field
            for result in state.eligibilityResults
            if result.overallStatus.value == "UNKNOWN"
            for field in result.missingFields
        ))
        if missing_fields:
            state.requiredFieldsForCurrentGoal = missing_fields[:2]
            state.needFollowUp = True
            state.followUpQuestions = [
                self._question_for(field, state)
                for field in missing_fields[:2]
            ]
            state.nextAction = "补充这些信息后即可继续核验当前政策资格。"
        state.stage = AgentStage.POLICY_COMPARING
        return state

    @classmethod
    def _question_for(cls, field: str, state: GovernmentAgentState) -> str:
        if field == "graduationDate" and state.userProfile.graduationYear is not None and state.userProfile.graduationMonth is not None:
            return "已确认毕业年月，但仍需提供精确毕业日期，以便准确核验毕业年限。"
        return cls._questions.get(field, f"请补充 {field} 信息。")
