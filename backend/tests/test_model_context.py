from __future__ import annotations

from app.agent.models import EligibilityResult, EligibilityStatus, KnowledgeEvidence, PolicyCandidate
from app.models.chat import UserProfile
from app.realtime_policy.models import RealtimePolicyHit
from app.services.model_context import ModelContextBuilder, ResponseMode
from app.services.policy_query_context import UserGoal
from app.agent.models import GovernmentAgentState


def policy() -> PolicyCandidate:
    return PolicyCandidate(
        policyId="policy-1", name="创业社会保险补贴", region="苏州市", department="人社部门",
        summary="补贴说明", effectiveDate="2026-01-01", sourceUrl="https://www.suzhou.gov.cn/policy",
        matchReason="与问题相关", conditions=["已缴纳社会保险"], requiredMaterials=["申请表"],
        process=["提交申请"], isMock=False,
    )


def state(goal: UserGoal) -> GovernmentAgentState:
    return GovernmentAgentState(
        sessionId="context-session", userMessage="创业社会保险补贴需要什么条件？",
        userProfile=UserProfile(city="苏州市", education="本科"), userGoal=goal,
        activeGoal=goal, activePolicy="policy-1", candidatePolicies=[policy()],
    )


def test_fact_context_contains_facts_and_evidence_but_not_eligibility_material_or_plan() -> None:
    item = state(UserGoal.POLICY_FACT)
    item.knowledgeEvidences = [KnowledgeEvidence(knowledgeId="k-1", policyName="创业培训补贴", sourceUrl="https://www.suzhou.gov.cn/k", currentness="CURRENT", chunkText="官方摘录", score=0.9)]
    context = ModelContextBuilder().build(item, [])

    assert context.responseMode is ResponseMode.DIRECT_ANSWER
    assert context.policyCandidates
    assert context.officialEvidence
    assert context.eligibilityResult == []
    assert context.materialResults == []
    assert context.plan is None
    assert "Dify" not in context.to_prompt_text()
    assert "score" not in context.to_prompt_text()


def test_job_search_context_keeps_profile_and_recommendations_only() -> None:
    item = state(UserGoal.JOB_SEARCH)
    item.eligibilityResults = [EligibilityResult(policyId="policy-1", overallStatus=EligibilityStatus.PASS, summary="符合")]
    context = ModelContextBuilder().build(item, [])

    assert context.responseMode is ResponseMode.RECOMMENDATION
    assert context.userProfile["地区"] == "苏州市"
    assert context.eligibilityResult == []
    assert context.materialResults == []
    assert context.plan is None


def test_eligibility_context_uses_deterministic_result_and_hides_unknown_fields() -> None:
    item = state(UserGoal.ELIGIBILITY_CHECK)
    item.eligibilityResults = [EligibilityResult(policyId="policy-1", overallStatus=EligibilityStatus.UNKNOWN, missingFields=["graduationDate"], summary="信息不足")]
    item.followUpQuestions = ["请提供毕业日期"]
    context = ModelContextBuilder().build(item, [])

    assert context.responseMode is ResponseMode.ELIGIBILITY_EXPLANATION
    assert context.eligibilityResult[0]["判断结果"] == "信息不足"
    assert context.missingRequiredFields == ["请提供毕业日期"]
    assert "UNKNOWN" not in context.to_prompt_text()


def test_history_is_trimmed_and_sessions_do_not_cross_context() -> None:
    history = [{"role": "user", "content": f"第{i}轮"} for i in range(12)]
    context = ModelContextBuilder(history_limit=4).build(state(UserGoal.POLICY_FACT), history)

    assert [message["content"] for message in context.conversationHistory] == ["第8轮", "第9轮", "第10轮", "第11轮"]


def test_realtime_evidence_is_standardized_without_raw_metadata() -> None:
    item = state(UserGoal.POLICY_FACT)
    item.realtimePolicyHits = [RealtimePolicyHit(
        hitId="hit", title="创业社会保险补贴官方通知", url="https://hrss.suzhou.gov.cn/notice", snippet="相关官方正文", domain="hrss.suzhou.gov.cn", freshnessReason="当前政策查询", retrievedAt="2026-10-05T00:00:00Z",
    )]
    context = ModelContextBuilder().build(item, [])

    evidence = context.officialEvidence[0]
    assert evidence["来源标题"] == "创业社会保险补贴官方通知"
    assert evidence["官方来源"].startswith("https://")
    assert "hitId" not in context.to_prompt_text()
