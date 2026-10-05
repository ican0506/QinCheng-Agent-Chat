from __future__ import annotations

from pathlib import Path

from app.agent.goal_policy_ranking import GoalAwarePolicyRanker
from app.agent.models import GovernmentAgentState, PolicyCandidate
from app.agent.presentation import PresentationAdapter
from app.agent.search_query import AgentSearchQueryBuilder
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.realtime_policy.models import RealtimePolicyHit
from app.services.policy_query_context import GoalResolver, UserGoal


def _hit(hit_id: str, title: str, snippet: str) -> RealtimePolicyHit:
    return RealtimePolicyHit(
        hitId=hit_id, title=title, snippet=snippet, url=f"https://www.suzhou.gov.cn/{hit_id}",
        domain="www.suzhou.gov.cn", freshnessReason="测试", retrievedAt="2026-10-05T00:00:00Z",
    )


def _candidate(policy_id: str, name: str) -> PolicyCandidate:
    return PolicyCandidate(
        policyId=policy_id, name=name, region="苏州市", department="苏州市人社局",
        summary="测试", effectiveDate="", sourceUrl="https://www.suzhou.gov.cn/test", matchReason="测试", isMock=False,
    )


def test_job_search_uses_actionable_official_query_and_no_startup_primary_recommendation() -> None:
    assert GoalResolver.resolve("我不想创业，只想就业") is UserGoal.JOB_SEARCH
    candidates = [
        _candidate("suzhou-employment-internship-2024", "就业见习"),
        _candidate("suzhou-startup-social-2021", "创业社会保险补贴"),
    ]
    repo = PolicyRepository(Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json")
    ranked = GoalAwarePolicyRanker(repo).rank(UserGoal.JOB_SEARCH, candidates)
    state = GovernmentAgentState(
        sessionId="job", userMessage="我快毕业了，不知道去哪找工作", userProfile=UserProfile(city="苏州市"),
        userGoal=UserGoal.JOB_SEARCH,
        candidatePolicies=ranked,
    )
    query = AgentSearchQueryBuilder().build(state)
    reply = PresentationAdapter.fallback_reply(state)

    assert "招聘" in query and "就业服务" in query and "就业见习" in query
    assert "创业社会保险补贴" not in reply
    assert "就业见习" in reply


def test_job_search_hides_consumer_and_technology_results_from_display() -> None:
    state = GovernmentAgentState(
        sessionId="job", userMessage="我快毕业了，不知道去哪找工作", userProfile=UserProfile(city="苏州市"),
        userGoal=UserGoal.JOB_SEARCH,
        realtimePolicyHits=[
            _hit("employment", "苏州市高校毕业生招聘活动", "毕业生就业服务和岗位对接"),
            _hit("car", "汽车购新补贴通知", "消费补贴安排"),
            _hit("tech", "独角兽企业申报", "科技项目企业申报"),
        ],
    )
    hits = PresentationAdapter._relevant_realtime_hits(state)

    assert [hit.hitId for hit in hits] == ["employment"]


def test_job_search_does_not_lead_with_historical_subsidy_when_employment_service_exists() -> None:
    state = GovernmentAgentState(
        sessionId="job-history", userMessage="我快毕业了，不知道去哪找工作", userProfile=UserProfile(),
        userGoal=UserGoal.JOB_SEARCH,
        candidatePolicies=[_candidate("historical", "历史补贴")],
        policyReferenceNotices={"historical": "该记录为历史申报通知，申报窗口已结束。"},
        realtimePolicyHits=[_hit("employment", "苏州市高校毕业生招聘活动", "提供岗位对接、就业服务和就业见习信息")],
    )

    reply = PresentationAdapter.fallback_reply(state)

    assert "申报窗口已结束" not in reply
    assert "就业见习" in reply
    assert "招聘" in reply or "就业服务" in reply


def test_discovery_without_profile_does_not_claim_personalized_recommendation() -> None:
    state = GovernmentAgentState(
        sessionId="discovery", userMessage="毕业生有什么就业支持", userProfile=UserProfile(),
        userGoal=UserGoal.POLICY_DISCOVERY, candidatePolicies=[_candidate("internship", "就业见习")],
    )

    reply = PresentationAdapter.fallback_reply(state)

    assert "根据你目前提供的信息" not in reply
    assert "目前可优先了解" in reply
