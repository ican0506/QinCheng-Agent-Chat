from __future__ import annotations

import asyncio
from datetime import date

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.chat import UserProfile
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.profile_update_parser import ProfileUpdateParser
from app.stores.session_store import InMemorySessionStore


class FailingProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "failing-profile-edit-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        raise RuntimeError("provider unavailable")

    async def stream(self, messages: list[LLMMessage]):
        raise RuntimeError("provider unavailable")
        yield ""


def settings() -> Settings:
    return Settings(
        llm_base_url="https://example.invalid",
        llm_api_key="key",
        llm_model="test",
        llm_timeout_seconds=1,
        llm_max_tokens=128,
        llm_temperature=0,
        cors_origins=("http://localhost:5173",),
        session_history_limit=20,
        session_limit=20,
    )


def test_profile_parser_normalizes_kunshan_month_and_unemployment_synonyms() -> None:
    patch = ProfileUpdateParser.parse(
        "我有昆山市户籍，2026年六月份毕业，目前没工作",
        current_date=date(2026, 10, 4),
    )

    assert patch["residencyRegistration"] == "本市户籍"
    assert patch["graduationYear"] == 2026
    assert patch["graduationMonth"] == 6
    assert "graduationDate" not in patch
    assert patch["employmentStatus"] == "待就业"


def test_complete_profile_message_is_merged_before_follow_up_is_calculated() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))

    response = client.post(
        "/api/agent/chat",
        json={
            "sessionId": "merged-profile-session",
            "userId": "profile-user",
            "message": "我在苏州，本科，今年毕业，待就业",
            "userProfile": {},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["userProfile"]["city"] == "苏州市"
    assert data["userProfile"]["education"] == "本科"
    assert data["userProfile"]["graduationYear"] == 2026
    assert data["userProfile"]["employmentStatus"] == "待就业"
    assert not any(
        word in question
        for word in ("城市", "学历", "毕业年份", "就业状态")
        for question in data["followUpQuestions"]
    )


def test_manual_profile_update_is_session_scoped_and_message_can_explicitly_override_it() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    session_a = "manual-profile-session-a"
    session_b = "manual-profile-session-b"
    user_id = "profile-user"

    updated = client.put(
        f"/api/agent/sessions/{session_a}/profile",
        json={
            "userId": user_id,
            "profile": {
                "city": "苏州市",
                "education": "硕士",
                "graduationYear": 2026,
                "graduationMonth": 6,
                "employmentStatus": "待就业",
            },
        },
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["userProfile"]["education"] == "硕士"
    assert updated.json()["data"]["userProfile"]["graduationMonth"] == 6

    # 旧的客户端快照不能覆盖刚手工确认的学历；本轮明确表达可以覆盖。
    stale = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_a,
            "userId": user_id,
            "message": "我想了解就业补贴",
            "userProfile": {"education": "本科"},
        },
    )
    assert stale.json()["data"]["userProfile"]["education"] == "硕士"

    corrected = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_a,
            "userId": user_id,
            "message": "之前说错了，其实我是本科",
            "userProfile": {},
        },
    )
    assert corrected.json()["data"]["userProfile"]["education"] == "本科"

    other = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_b,
            "userId": user_id,
            "message": "我在苏州，准备创业",
            "userProfile": {},
        },
    )
    profile_b = other.json()["data"]["userProfile"]
    assert profile_b["city"] == "苏州市"
    assert profile_b["education"] is None
    assert profile_b["graduationYear"] is None


def test_manual_employment_update_clears_stale_unemployment_status() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    session_id = "manual-employment-correction"
    user_id = "test-user"

    initial = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": user_id,
            "message": "我目前待就业",
            "userProfile": {},
        },
    )
    assert initial.status_code == 200

    corrected = client.put(
        f"/api/agent/sessions/{session_id}/profile",
        json={"userId": user_id, "profile": {"employmentStatus": "已就业"}},
    )
    assert corrected.status_code == 200

    store = client.app.state.chat_service._store
    profile = asyncio.run(store.get_internal_profile(session_id, user_id))
    assert profile.employmentStatus == "已就业"
    assert profile.unemploymentStatus is None


def test_manual_employment_update_recomputes_eligibility_with_new_status() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))
    session_id = "manual-employment-workflow"
    user_id = "test-user"

    initial = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": user_id,
            "message": "我在苏州，本科，2026年毕业，待就业，我符合灵活就业社保补贴吗？",
            "userProfile": {},
        },
    )
    assert initial.status_code == 200
    assert any(
        item["policyId"] == "suzhou-flexible-social-2021"
        for item in initial.json()["data"]["eligibility"]
    )

    updated = client.put(
        f"/api/agent/sessions/{session_id}/profile",
        json={"userId": user_id, "profile": {"employmentStatus": "已就业"}},
    )
    assert updated.status_code == 200
    eligibility = next(
        item
        for item in updated.json()["data"]["eligibility"]
        if item["policyId"] == "suzhou-flexible-social-2021"
    )
    unemployment = next(
        condition
        for condition in eligibility["conditionResults"]
        if condition["description"] == "未就业高校毕业生。"
    )
    assert unemployment["status"] != "PASS"


def test_session_store_deletion_is_idempotent_and_isolated() -> None:
    async def scenario() -> None:
        store = InMemorySessionStore()
        await store.set_internal_profile("session-a", "same-user", UserProfile(city="苏州市"))
        await store.set_material_declarations("session-a", "same-user", {"material-a": True})
        await store.append_exchange("session-a", "same-user", "A", "reply A")
        await store.set_internal_profile("session-b", "same-user", UserProfile(education="本科"))
        await store.append_exchange("session-b", "same-user", "B", "reply B")

        assert await store.delete_session("session-a", "same-user") is True
        assert await store.delete_session("session-a", "same-user") is False
        assert await store.get_messages("session-a", "same-user") == []
        assert (await store.get_internal_profile("session-a", "same-user")).city is None
        assert await store.get_material_declarations("session-a", "same-user") == {}
        assert (await store.get_internal_profile("session-b", "same-user")).education == "本科"
        assert len(await store.get_messages("session-b", "same-user")) == 2

    asyncio.run(scenario())


def test_delete_session_api_is_safe_for_missing_session() -> None:
    client = TestClient(create_app(settings(), FailingProvider()))

    missing = client.delete("/api/agent/sessions/not-created", params={"userId": "profile-user"})

    assert missing.status_code == 200
    assert missing.json()["data"] == {"deleted": False}
