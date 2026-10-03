from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.agent.models import GovernmentAgentState, PolicyCandidate
from app.main import create_app
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.realtime_policy.models import SearchResult
from app.realtime_policy.provider import FakeRealtimeSearchProvider
from app.realtime_policy.tool import OfficialRealtimePolicySearchTool
from app.services.chat_service import ChatService
from app.services.policy_query_context import PolicyDomainIntent, PolicyQueryMode, PolicyQueryModeDetector
from app.services.profile_update_parser import ProfileUpdateParser
from test_real_workflow_tools import settings
from test_release_regression import FailingProvider


ROOT = Path(__file__).resolve().parents[1] / "data" / "policies"


def _client(provider: FakeRealtimeSearchProvider | None = None) -> TestClient:
    config = replace(
        settings(),
        profile_extraction_enabled=False,
        realtime_policy_search_enabled=provider is not None,
    )
    return TestClient(
        create_app(config, FailingProvider(), realtime_provider=provider)
    )


def _send(
    client: TestClient,
    message: str,
    *,
    session_id: str = "competition-rc-p1-session",
) -> dict:
    response = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": "competition-rc-p1-user",
            "message": message,
            "userProfile": {},
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_policy_query_mode_distinguishes_fact_and_personalized_queries() -> None:
    assert PolicyQueryModeDetector.detect(
        "创业社会保险补贴需要什么条件？"
    ) is PolicyQueryMode.FACT_QUERY
    assert PolicyQueryModeDetector.detect(
        "苏州创业社会保险补贴现在还能申请吗？"
    ) is PolicyQueryMode.FACT_QUERY
    assert PolicyQueryModeDetector.detect(
        "我符合创业社会保险补贴吗？"
    ) is PolicyQueryMode.PERSONALIZED_QUERY
    assert PolicyQueryModeDetector.detect(
        "我现在能申请什么补贴？"
    ) is PolicyQueryMode.PERSONALIZED_QUERY


@pytest.mark.parametrize(
    "message",
    [
        "我自己按灵活就业交社保，有什么补贴？",
        "就业见习适合哪些毕业生？",
    ],
)
def test_policy_information_questions_are_fact_queries_without_profile_gate(
    message: str,
) -> None:
    assert PolicyQueryModeDetector.detect(message) is PolicyQueryMode.FACT_QUERY


def test_new_session_fact_query_searches_local_policy_without_base_profile_follow_up() -> None:
    provider = FakeRealtimeSearchProvider([])
    client = _client(provider)

    data = _send(client, "创业社会保险补贴需要什么条件？")

    assert provider.call_count == 0
    assert data["needFollowUp"] is False
    assert data["followUpQuestions"] == []
    assert any(
        policy["policyId"] == "suzhou-startup-social-2021"
        for policy in data["policies"]
    )
    assert "连续缴纳" in data["replyText"]


@pytest.mark.parametrize(
    ("message", "expected_policy_id"),
    [
        ("我自己按灵活就业交社保，有什么补贴？", "suzhou-flexible-social-2021"),
        ("就业见习适合哪些毕业生？", "suzhou-employment-internship-2024"),
    ],
)
def test_new_session_policy_information_query_searches_without_profile_follow_up(
    message: str, expected_policy_id: str,
) -> None:
    data = _send(_client(), message)

    assert data["needFollowUp"] is False
    assert data["followUpQuestions"] == []
    assert any(policy["policyId"] == expected_policy_id for policy in data["policies"])


def test_incomplete_profile_historical_fact_query_keeps_closed_notice_in_reply() -> None:
    data = _send(_client(), "2026届求职创业补贴什么时候申报？")

    assert data["needFollowUp"] is False
    assert any(
        policy["policyId"] == "suzhou-job-seeking-subsidy-2026"
        for policy in data["policies"]
    )
    assert "历史申报通知" in data["replyText"]
    assert "申报窗口已结束" in data["replyText"]
    assert "当前开放申领" not in data["replyText"]


def test_fact_query_keeps_historical_closed_notice_with_mixed_candidates() -> None:
    historical = PolicyCandidate(
        policyId="suzhou-job-seeking-subsidy-2026",
        name="求职创业补贴（2026届毕业生申领通知）",
        region="苏州市",
        department="人社部门",
        summary="历史通知",
        effectiveDate="",
        sourceUrl="https://example.invalid/historical",
        matchReason="test",
        isMock=False,
    )
    current = historical.model_copy(
        update={
            "policyId": "suzhou-startup-social-2021",
            "name": "创业社会保险补贴",
            "sourceUrl": "https://example.invalid/current",
        }
    )
    state = GovernmentAgentState(
        sessionId="historical-fact-mixed",
        userMessage="2026届求职创业补贴什么时候申报？",
        userProfile=UserProfile(),
        domainIntent=PolicyDomainIntent.IN_SCOPE,
        queryMode=PolicyQueryMode.FACT_QUERY,
        candidatePolicies=[historical, current],
        policyReferenceNotices={
            historical.policyId: "当前知识库中的该记录为历史申报通知，申报窗口已结束。"
        },
    )

    reply = ChatService._fallback_reply(state)

    assert "历史申报通知" in reply
    assert "申报窗口已结束" in reply


def test_new_session_current_fact_query_calls_realtime_once() -> None:
    provider = FakeRealtimeSearchProvider(
        [
            SearchResult(
                title="创业社会保险补贴申领办事指南",
                url="https://www.suzhou.gov.cn/current-startup-social",
                snippet="当前申报安排",
                publishedAt=date(2026, 6, 17),
            )
        ]
    )
    client = _client(provider)

    data = _send(client, "苏州创业社会保险补贴现在还能申请吗？")

    assert provider.call_count == 1
    assert data["needFollowUp"] is False
    assert any(
        policy["policyId"] == "suzhou-startup-social-2021"
        for policy in data["policies"]
    )
    assert "current-startup-social" in data["replyText"]


def test_personalized_policy_query_still_requires_base_profile() -> None:
    client = _client()

    data = _send(client, "我符合创业社会保险补贴吗？")

    assert data["needFollowUp"] is True
    assert data["policies"] == []
    assert any("学历" in question for question in data["followUpQuestions"])


def test_complete_startup_profile_excludes_pure_flexible_employment_policy() -> None:
    client = _client()

    data = _send(
        client,
        "我在苏州，本科，2025年6月20日毕业，目前创业中，准备创业，"
        "连续缴纳社保12个月，公司注册12个月",
    )

    policy_ids = {policy["policyId"] for policy in data["policies"]}
    assert "suzhou-startup-social-2021" in policy_ids
    assert "suzhou-flexible-social-2021" not in policy_ids
    assert not any(
        "灵活就业" in question or "未就业状态" in question
        for question in data["followUpQuestions"]
    )
    assert not any(
        "suzhou-flexible-social-2021" in step["policyIds"]
        for step in (data["plan"] or {"steps": []})["steps"]
    )


def test_explicit_startup_and_flexible_employment_keeps_both_directions() -> None:
    client = _client()

    data = _send(
        client,
        "我在苏州，本科，2025年6月20日毕业，目前创业中，准备创业，"
        "同时以灵活就业身份参保缴费，连续缴纳社保12个月，公司注册12个月，"
        "两个方向都帮我看看",
    )

    policy_ids = {policy["policyId"] for policy in data["policies"]}
    assert "suzhou-startup-social-2021" in policy_ids
    assert "suzhou-flexible-social-2021" in policy_ids


def test_non_startup_flexible_employment_scenario_keeps_existing_behavior() -> None:
    client = _client()

    data = _send(
        client,
        "我不是创业，我在苏州，本科，2025年6月20日毕业，目前待业，"
        "只是自己按灵活就业交社保",
    )

    policy_ids = {policy["policyId"] for policy in data["policies"]}
    assert "suzhou-flexible-social-2021" in policy_ids
    assert "suzhou-startup-social-2021" not in policy_ids


def _realtime_tool(provider: FakeRealtimeSearchProvider) -> OfficialRealtimePolicySearchTool:
    return OfficialRealtimePolicySearchTool(
        provider,
        PolicyRepository(ROOT / "policies.json"),
        ["suzhou.gov.cn"],
    )


def _historical_results() -> list[SearchResult]:
    return [
        SearchResult(
            title="2027届求职创业补贴通知",
            url="https://www.suzhou.gov.cn/2027-notice",
            snippet="2027届申报通知",
            publishedAt=date(2026, 9, 1),
        ),
        SearchResult(
            title="2026年高校毕业生就业工作通知",
            url="https://www.suzhou.gov.cn/2026-employment",
            snippet="高校毕业生就业工作",
            publishedAt=date(2026, 5, 1),
        ),
        SearchResult(
            title="2026届求职创业补贴申报通知",
            url="https://www.suzhou.gov.cn/2026-job-seeking-notice",
            snippet="求职创业补贴申报安排",
            publishedAt=date(2025, 8, 23),
        ),
        SearchResult(
            title="创业校友分享",
            url="https://www.suzhou.gov.cn/alumni",
            snippet="校友经验分享",
            publishedAt=date(2026, 9, 30),
        ),
        SearchResult(
            title="就业创业栏目",
            url="https://www.suzhou.gov.cn/channel",
            snippet="就业创业栏目",
        ),
    ]


def test_historical_realtime_ranking_prioritizes_exact_cohort_notice() -> None:
    provider = FakeRealtimeSearchProvider(_historical_results())

    _, hits = asyncio.run(
        _realtime_tool(provider).search(
            UserProfile(city="苏州市"),
            "我想看2026届求职创业补贴之前的申报通知",
            "官方历史通知查询",
        )
    )

    assert hits[0].title == "2026届求职创业补贴申报通知"
    assert [hit.title for hit in hits].index("2027届求职创业补贴通知") > 0


def test_historical_ranking_prioritizes_exact_related_record_when_page_title_has_no_cohort() -> None:
    repository = PolicyRepository(ROOT / "policies.json")
    historical = repository.get_by_id("suzhou-job-seeking-subsidy-2026")
    assert historical is not None and historical.sourceUrl
    provider = FakeRealtimeSearchProvider(
        [
            SearchResult(
                title="9月1日起，一次性求职补贴启动申请！",
                url="https://www.suzhou.gov.cn/newer-general-notice",
                snippet="最新求职补贴申报安排",
                publishedAt=date(2026, 8, 28),
            ),
            SearchResult(
                title="求职补贴！线上申报！",
                url=historical.sourceUrl,
                snippet="补贴申报入口与操作说明",
                publishedAt=date(2025, 8, 27),
            ),
        ]
    )

    _, hits = asyncio.run(
        _realtime_tool(provider).search(
            UserProfile(city="苏州市"),
            "我想看2026届求职创业补贴之前的申报通知",
            "官方历史通知查询",
        )
    )

    assert hits[0].relatedPolicyId == historical.policyId


def test_current_realtime_query_does_not_use_historical_cohort_ranking() -> None:
    provider = FakeRealtimeSearchProvider(_historical_results())

    _, hits = asyncio.run(
        _realtime_tool(provider).search(
            UserProfile(city="苏州市"),
            "2026年苏州毕业生最新就业政策是什么？",
            "政策当前性查询",
        )
    )

    assert hits[0].title != "2026届求职创业补贴申报通知"


def test_negative_employment_and_flexible_insurance_correction_clears_history() -> None:
    client = _client()
    session_id = "competition-negative-correction"
    service = client.app.state.chat_service

    _send(
        client,
        "我在苏州，本科，2025年6月20日毕业，目前待业，"
        "并且以灵活就业身份参保缴费",
        session_id=session_id,
    )
    data = _send(
        client,
        "我有苏州市户籍，目前不是未就业，也不是灵活就业参保，"
        "只看创业社会保险补贴",
        session_id=session_id,
    )
    profile = asyncio.run(
        service._store.get_internal_profile(
            session_id, "competition-rc-p1-user"
        )
    )

    assert profile.residencyRegistration == "本市户籍"
    assert profile.employmentStatus is None
    assert profile.unemploymentStatus is None
    assert profile.flexibleEmploymentInsurance is False
    assert not any("户籍" in question for question in data["followUpQuestions"])
    assert {policy["policyId"] for policy in data["policies"]} == {
        "suzhou-startup-social-2021"
    }


def test_negative_scope_parser_handles_required_phrases() -> None:
    for message in (
        "不是未就业",
        "不是待就业",
        "已经不是待业状态",
    ):
        patch = ProfileUpdateParser.parse(message)
        assert "employmentStatus" in patch and patch["employmentStatus"] is None
        assert "unemploymentStatus" in patch and patch["unemploymentStatus"] is None

    for message in (
        "不是灵活就业参保",
        "没有按灵活就业参保",
        "我不是灵活就业人员",
        "目前不属于灵活就业",
    ):
        assert ProfileUpdateParser.flexible_insurance_overrides(message) == {
            "flexibleEmploymentInsurance": False
        }

    assert ProfileUpdateParser.parse("我有苏州市户籍")[
        "residencyRegistration"
    ] == "本市户籍"
