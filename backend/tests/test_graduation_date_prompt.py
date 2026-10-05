from __future__ import annotations

import asyncio
from datetime import date

from app.agent.models import EligibilityResult, EligibilityStatus, GovernmentAgentState
from app.agent.nodes.eligibility import EligibilityNode
from app.models.chat import UserProfile
from app.services.policy_query_context import RouteDecision, UserGoal


class MissingGraduationDateTool:
    async def check(self, profile, policies):
        return [EligibilityResult(
            policyId="target", overallStatus=EligibilityStatus.UNKNOWN, missingFields=["graduationDate"], summary="缺少精确日期",
        )]


def test_graduation_month_is_acknowledged_when_exact_date_is_required() -> None:
    state = GovernmentAgentState(
        sessionId="graduation", userMessage="2026年6月毕业", userProfile=UserProfile(graduationYear=2026, graduationMonth=6),
        userGoal=UserGoal.ELIGIBILITY_CHECK,
        routeDecision=RouteDecision(runEligibility=True),
    )

    result = asyncio.run(EligibilityNode(MissingGraduationDateTool()).execute(state))

    assert result.followUpQuestions == ["已确认毕业年月，但仍需提供精确毕业日期，以便准确核验毕业年限。"]
