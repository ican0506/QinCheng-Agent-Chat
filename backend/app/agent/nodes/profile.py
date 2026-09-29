from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState


class ProfileNode:
    _questions = {
        "city": "请问您所在的城市是哪里？",
        "education": "请问您的学历是本科、硕士、专科还是其他？",
        "graduationYear": "请问您的毕业年份是？",
        "employmentStatus": "请问您目前是待就业、已就业还是创业中？",
    }

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        missing = [field for field in self._questions if getattr(state.userProfile, field) in (None, "")]
        state.stage = AgentStage.PROFILE_COLLECTING
        if missing:
            state.needFollowUp = True
            state.followUpQuestions = [self._questions[field] for field in missing]
            state.nextAction = "补充个人画像后继续检索相关政策。"
            return state
        state.needFollowUp = False
        state.followUpQuestions = []
        state.stage = AgentStage.POLICY_SEARCHING
        return state
