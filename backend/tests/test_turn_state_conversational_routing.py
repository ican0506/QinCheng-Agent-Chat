from __future__ import annotations

import asyncio
from dataclasses import replace

from fastapi.testclient import TestClient

from app.agent.models import GovernmentAgentState, PolicyCandidate
from app.agent.presentation import PresentationAdapter
from app.agent.workflow import WorkflowAgent
from app.main import create_app
from app.models.chat import UserProfile
from app.services.model_context import ModelContextBuilder, ResponseMode
from app.services.policy_query_context import GoalResolver, RouteDecider, UserGoal
from app.realtime_policy.models import RealtimePolicyHit
from test_real_workflow_tools import settings
from test_release_regression import FailingProvider


def client() -> TestClient:
    return TestClient(create_app(replace(settings(), profile_extraction_enabled=False), FailingProvider()))


def send(active_client: TestClient, message: str, session_id: str) -> dict:
    response = active_client.post(
        "/api/agent/chat",
        json={"sessionId": session_id, "userId": "turn-state-user", "message": message, "userProfile": {}},
    )
    assert response.status_code == 200
    return response.json()["data"]


def candidate() -> PolicyCandidate:
    return PolicyCandidate(
        policyId="old-policy", name="旧政策", region="苏州市", department="人社部门",
        summary="旧摘要", effectiveDate="2026-01-01", sourceUrl="https://www.suzhou.gov.cn/old",
        matchReason="旧命中", isMock=False,
    )


def test_conversational_goal_has_no_business_capabilities() -> None:
    goal = GoalResolver.resolve("你好")
    route = RouteDecider.decide(goal)

    assert goal is UserGoal.CONVERSATIONAL
    assert route.runPolicySearch is False
    assert route.runEligibility is False
    assert route.runMaterialCheck is False
    assert route.runPlan is False


def test_turn_reset_clears_results_but_preserves_profile_and_active_task() -> None:
    state = GovernmentAgentState(
        sessionId="turn-reset", userMessage="你好", userProfile=UserProfile(city="苏州市"),
        activeGoal=UserGoal.ELIGIBILITY_CHECK, activePolicy="keep-policy",
        candidatePolicies=[candidate()], finalReply="旧回复", realtimeSearchMs=91,
        needFollowUp=True, followUpQuestions=["旧追问"],
    )
    state.reset_turn_results()

    assert state.userProfile.city == "苏州市"
    assert state.activeGoal is UserGoal.ELIGIBILITY_CHECK
    assert state.activePolicy == "keep-policy"
    assert state.candidatePolicies == []
    assert state.finalReply is None
    assert state.realtimeSearchMs == 0
    assert state.followUpQuestions == []


def test_greeting_bypasses_all_policy_nodes() -> None:
    state = asyncio.run(WorkflowAgent.default().run("greeting", "你好", UserProfile()))

    assert state.userGoal is UserGoal.CONVERSATIONAL
    assert state.candidatePolicies == []
    assert state.eligibilityResults == []
    assert state.materialResults == []
    assert state.overallPlan is None
    assert state.realtimeSearchMs == 0
    assert "你好" in (state.finalReply or "")


def test_meta_correction_does_not_search_or_reuse_stale_results() -> None:
    active_client = client()
    first = send(active_client, "2026届求职创业补贴什么时候申报？", "meta-session")
    assert first["policies"]

    data = send(active_client, "我都没给你说我是什么情况你怎么就知道", "meta-session")
    assert data["policies"] == []
    assert data["eligibility"] == []
    assert data["materialResults"] == []
    assert data["plan"] is None
    assert "历史申报通知" not in data["replyText"]
    assert "不应该作个性化推断" in data["replyText"]


def test_conversational_context_hides_stale_policy_state() -> None:
    state = GovernmentAgentState(
        sessionId="context", userMessage="谢谢", userProfile=UserProfile(city="苏州市"),
        userGoal=UserGoal.CONVERSATIONAL, activeGoal=UserGoal.POLICY_FACT,
        candidatePolicies=[candidate()], realtimePolicyHits=[],
    )
    context = ModelContextBuilder().build(state, [{"role": "assistant", "content": "旧政策"}])

    assert context.responseMode is ResponseMode.CONVERSATIONAL
    assert context.userProfile == {}
    assert context.policyCandidates == []
    assert context.officialEvidence == []
    assert context.activeGoal is None


def test_session_b_greeting_does_not_inherit_session_a_results() -> None:
    active_client = client()
    left = send(active_client, "创业社会保险补贴需要什么条件？", "session-a")
    right = send(active_client, "你好", "session-b")

    assert left["policies"]
    assert right["policies"] == []
    assert right["eligibility"] == []
    assert right["plan"] is None
    assert right["userProfile"]["city"] is None


def test_realtime_evidence_requires_current_topic_relevance() -> None:
    relevant = RealtimePolicyHit(
        hitId="relevant", title="苏州市创业社会保险补贴", url="https://www.suzhou.gov.cn/a",
        snippet="创业人员社会保险补贴办理说明", domain="www.suzhou.gov.cn",
        freshnessReason="当前查询", retrievedAt="2026-10-05T00:00:00Z",
    )
    unrelated = RealtimePolicyHit(
        hitId="unrelated", title="独角兽企业申报通知", url="https://www.suzhou.gov.cn/b",
        snippet="高技能人才项目安排", domain="www.suzhou.gov.cn",
        freshnessReason="当前查询", retrievedAt="2026-10-05T00:00:00Z",
    )

    state = GovernmentAgentState(
        sessionId="relevance", userMessage="创业社会保险补贴现在还能申请吗？",
        userProfile=UserProfile(), realtimePolicyHits=[relevant, unrelated],
    )
    filtered = PresentationAdapter._relevant_realtime_hits(state)

    assert [hit.hitId for hit in filtered] == ["relevant"]
