"""实时官方结果的用户展示相关性边界；保留 state 原始结果用于审计。"""
from __future__ import annotations

from app.agent.models import GovernmentAgentState
from app.realtime_policy.models import RealtimePolicyHit
from app.services.policy_query_context import UserGoal


def relevant_realtime_hits(state: GovernmentAgentState, *, limit: int | None = None) -> list[RealtimePolicyHit]:
    """只返回可进入回复或模型上下文的主题相关官方证据。"""
    if state.userGoal is UserGoal.JOB_SEARCH:
        blocked = ("汽车购新", "以旧换新", "消费补贴", "独角兽", "科技项目", "企业申报")
        employment = ("就业", "招聘", "岗位", "见习", "毕业生", "人社", "求职")
        hits = [
            hit for hit in state.realtimePolicyHits
            if not any(word in f"{hit.title} {hit.snippet}" for word in blocked)
            and any(word in f"{hit.title} {hit.snippet}" for word in employment)
        ]
    else:
        topics = (
            "就业", "创业", "毕业", "见习", "社保", "社会保险", "补贴", "求职", "申报", "申请", "灵活就业",
        )
        requested = {topic for topic in topics if topic in state.userMessage}
        hits = [] if not requested else [
            hit for hit in state.realtimePolicyHits
            if hit.relatedPolicyId is not None or any(topic in f"{hit.title} {hit.snippet}" for topic in requested)
        ]
    return hits if limit is None else hits[:limit]
