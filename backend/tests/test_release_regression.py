from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.base import LLMMessage, LLMProvider


class FailingProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "failing-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        raise RuntimeError("provider unavailable")

    async def stream(self, messages: list[LLMMessage]):
        raise RuntimeError("provider unavailable")
        yield ""


class MisleadingProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "misleading-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        return "推荐求职创业补贴、就业见习补贴……"


class StaleNoticeProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "stale-notice-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        return "请关注后续发布的2025届对应批次通知。"


def settings() -> Settings:
    return Settings(llm_base_url="https://example.invalid", llm_api_key="key", llm_model="test", llm_timeout_seconds=1, llm_max_tokens=128, llm_temperature=0, cors_origins=("http://localhost:5173",), session_history_limit=20, session_limit=20)


def payload(message: str, profile: dict | None = None, session: str = "competition-session") -> dict:
    return {"sessionId": session, "userId": "competition-user", "message": message, "userProfile": {"city": "苏州市", "education": "本科", "graduationYear": 2026, "employmentStatus": "创业中", **(profile or {})}}


def test_llm_failure_keeps_structured_chat_and_sse_results() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    response = client.post("/api/agent/chat", json=payload("我想申请一次性创业补贴", {"graduationDate": "2025-06-30", "businessRegistrationMonths": 12}))
    assert response.status_code == 200
    assert response.json()["data"]["policies"]
    assert response.json()["data"]["replyText"]
    stream = client.post("/api/agent/chat/stream", json=payload("我想申请一次性创业补贴", {"graduationDate": "2025-06-30", "businessRegistrationMonths": 12}))
    assert "event: done" in stream.text


def test_follow_up_profile_is_retained_server_side_across_turns() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    first = client.post("/api/agent/chat", json=payload("我想申请创业社会保险补贴", {"businessRegistrationMonths": 8})).json()["data"]
    assert first["needFollowUp"] is True
    second = client.post("/api/agent/chat", json=payload("我是2025年6月30日毕业的", {"businessRegistrationMonths": 8})).json()["data"]
    assert any(item["policyId"] == "suzhou-startup-social-2021" for item in second["eligibility"])
    third = client.post("/api/agent/chat", json=payload("我交了12个月社保，继续申请创业社会保险补贴", {"businessRegistrationMonths": 8})).json()["data"]
    result = next(item for item in third["eligibility"] if item["policyId"] == "suzhou-startup-social-2021")
    assert result["overallStatus"] == "PASS"


def test_follow_up_guard_rejects_llm_policy_recommendations() -> None:
    client = TestClient(create_app(settings(), MisleadingProvider()))
    response = client.post("/api/agent/chat", json=payload("我想咨询政策", {"city": None, "education": None, "graduationYear": None, "employmentStatus": None}))
    data = response.json()["data"]
    assert data["needFollowUp"] is True
    assert data["policies"] == []
    assert "推荐求职创业补贴" not in data["replyText"]
    assert "补充" in data["replyText"]


def test_historical_closed_policy_uses_deterministic_current_notice() -> None:
    client = TestClient(create_app(settings(), StaleNoticeProvider()))
    response = client.post(
        "/api/agent/chat",
        json={
            "sessionId": "historical-closed-reply",
            "userId": "historical-closed-user",
            "message": "我想申请求职创业补贴",
            "userProfile": {
                "city": "苏州市",
                "education": "本科",
                "graduationYear": 2026,
                "employmentStatus": "待就业",
                "jobSeekingIntent": True,
                "hardshipIdentity": "低保家庭",
            },
        },
    )
    data = response.json()["data"]

    assert data["needFollowUp"] is False
    assert "后续发布的2025届" not in data["replyText"]
    assert data["replyText"] == "当前知识库中的该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。"


def test_server_profile_is_accumulated_across_browser_style_three_turns() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    session_id = "browser-profile-turns"
    user_id = "browser-profile-user"

    first = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": user_id,
            "message": "我是今年毕业生，想了解本地就业补贴",
            "userProfile": {},
        },
    ).json()["data"]
    assert first["needFollowUp"] is True

    second = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": user_id,
            "message": "我在苏州，本科，2025年6月毕业，目前未就业",
            "userProfile": {},
        },
    ).json()["data"]
    second_profile = asyncio.run(
        client.app.state.chat_service._store.get_internal_profile(session_id, user_id)
    )
    assert second["userProfile"]["city"] == "苏州市"
    assert second["userProfile"]["education"] == "本科"
    assert second["userProfile"]["graduationYear"] == 2025
    assert second["userProfile"]["employmentStatus"] == "待就业"
    assert second_profile.city == "苏州市"
    assert second_profile.education == "本科"
    assert second_profile.graduationYear == 2025
    assert second_profile.graduationDate is None
    assert second_profile.employmentStatus == "待就业"
    assert second_profile.unemploymentStatus == "未就业"
    assert not any(
        term in question
        for term in ("城市", "学历", "毕业年份", "就业状态")
        for question in second["followUpQuestions"]
    )

    client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": user_id,
            "message": "我已经连续缴纳社保12个月",
            "userProfile": {},
        },
    )
    third_profile = asyncio.run(
        client.app.state.chat_service._store.get_internal_profile(session_id, user_id)
    )
    assert third_profile.socialInsuranceMonths == 12
    assert third_profile.city == "苏州市"
    assert third_profile.education == "本科"
    assert third_profile.graduationYear == 2025
    assert third_profile.employmentStatus == "待就业"


def test_latest_non_entrepreneurial_intent_removes_startup_candidates_and_plan_steps() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    session_id = "intent-correction-turns"
    user_id = "intent-correction-user"
    request = lambda message: {
        "sessionId": session_id,
        "userId": user_id,
        "message": message,
        "userProfile": {},
    }

    client.post("/api/agent/chat", json=request("我是今年毕业生，想了解本地就业补贴"))
    client.post("/api/agent/chat", json=request("我在苏州，本科，2025年6月毕业，目前未就业"))
    third = client.post("/api/agent/chat", json=request("我已经连续缴纳社保12个月")).json()["data"]
    assert third["policies"]

    fourth = client.post("/api/agent/chat", json=request("我不创业，只打算找工作")).json()["data"]
    profile = asyncio.run(
        client.app.state.chat_service._store.get_internal_profile(session_id, user_id)
    )
    excluded_ids = {"suzhou-startup-one-time-2023", "suzhou-startup-social-2021"}
    returned_ids = {item["policyId"] for item in fourth["policies"]}
    planned_ids = {policy_id for step in (fourth["plan"] or {"steps": []})["steps"] for policy_id in step["policyIds"]}

    assert profile.entrepreneurshipIntent is False
    assert profile.jobSeekingIntent is True
    assert returned_ids.isdisjoint(excluded_ids)
    assert not any("经营主体" in question or "首次创业" in question or "企业注册" in question for question in fourth["followUpQuestions"])
    assert planned_ids.isdisjoint(excluded_ids)
    assert "经营主体" not in fourth["replyText"]


def test_new_entrepreneurial_session_does_not_inherit_another_sessions_profile() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    client.post(
        "/api/agent/chat",
        json={
            "sessionId": "profile-source-session",
            "userId": "same-user",
            "message": "我在苏州，本科，2025年6月毕业，目前未就业，连续缴纳社保12个月",
            "userProfile": {},
        },
    )
    client.post(
        "/api/agent/chat",
        json={
            "sessionId": "new-entrepreneurial-session",
            "userId": "same-user",
            "message": "我在苏州，准备创业",
            "userProfile": {},
        },
    )
    profile = asyncio.run(
        client.app.state.chat_service._store.get_internal_profile("new-entrepreneurial-session", "same-user")
    )

    assert profile.city == "苏州市"
    assert profile.entrepreneurshipIntent is True
    assert profile.education is None
    assert profile.graduationYear is None
    assert profile.socialInsuranceMonths is None
