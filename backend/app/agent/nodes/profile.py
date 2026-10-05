from __future__ import annotations

from app.agent.models import AgentStage, GovernmentAgentState
from app.services.policy_query_context import UserGoal


class ProfileNode:
    _questions = {
        "city": "请问您所在的城市是哪里？",
        "education": "请问您的学历是本科、硕士、专科还是其他？",
        "graduationYear": "请问您的毕业年份是？",
        "employmentStatus": "请问您目前是待就业、已就业还是创业中？",
    }

    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState:
        # 画像是可增量使用的上下文，不是普通咨询的前置闸门。
        # 只有资格核验节点在已知候选政策后，才会提出真正影响判断的字段。
        state.needFollowUp = False
        state.followUpQuestions = []
        state.requiredFieldsForCurrentGoal = []
        if state.userGoal is UserGoal.PROFILE_UPDATE:
            state.nextAction = "已更新个人情况，可继续咨询你想了解的就业创业政策。"
        else:
            state.nextAction = None
        state.stage = AgentStage.POLICY_SEARCHING
        return state
