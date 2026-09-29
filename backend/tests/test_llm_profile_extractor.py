from __future__ import annotations

import asyncio
import json

import pytest

from app.agent.workflow import WorkflowAgent
from app.core.config import Settings
from app.main import create_app
from app.models.chat import ChatRequest, UserProfile
from app.services.chat_service import ChatService
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm_profile_extractor import LLMProfileExtractor, ProfileExtractionError
from app.stores.session_store import InMemorySessionStore
from fastapi.testclient import TestClient


class StructuredProvider(LLMProvider):
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls: list[list[LLMMessage]] = []

    @property
    def name(self) -> str:
        return "structured-profile-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.calls.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class RoutedStructuredProvider(LLMProvider):
    def __init__(self, extraction_responses: list[str]) -> None:
        self._extraction_responses = iter(extraction_responses)
        self.calls: list[list[LLMMessage]] = []

    @property
    def name(self) -> str:
        return "routed-structured-profile-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.calls.append(messages)
        if messages[0]["content"].startswith("你是用户画像信息抽取器"):
            return next(self._extraction_responses)
        return "已基于结构化 Agent 结果生成说明。"


def extract(message: str, response: dict[str, object], profile: UserProfile | None = None) -> dict[str, object]:
    provider = StructuredProvider(json.dumps(response, ensure_ascii=False))
    return asyncio.run(LLMProfileExtractor(provider).extract(message, profile or UserProfile()))


@pytest.mark.parametrize(
    ("message", "response", "expected"),
    [
        ("我在苏州，本科", {"city": "苏州市", "education": "本科"}, {"city": "苏州市", "education": "本科"}),
        ("2025年6月毕业", {"graduationYear": 2025, "graduationDate": None}, {"graduationYear": 2025}),
        ("2025年6月20日毕业", {"graduationYear": 2025, "graduationDate": "2025-06-20"}, {"graduationYear": 2025, "graduationDate": "2025-06-20"}),
        ("目前没工作", {"employmentStatus": "未就业"}, {"employmentStatus": "待就业", "unemploymentStatus": "未就业"}),
        ("社保交了12个月", {"socialInsuranceMonths": 12}, {"socialInsuranceMonths": 12}),
        ("我不创业，只想找工作", {"entrepreneurshipIntent": False, "jobSeekingIntent": True}, {"entrepreneurshipIntent": False, "jobSeekingIntent": True}),
        ("准备创业", {"entrepreneurshipIntent": True}, {"entrepreneurshipIntent": True}),
    ],
)
def test_extractor_returns_only_validated_normalized_profile_patch(
    message: str, response: dict[str, object], expected: dict[str, object]
) -> None:
    patch = extract(message, response)

    normalized = {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in patch.items()}
    assert normalized == expected


@pytest.mark.parametrize(
    "response",
    [
        "not-json",
        '{"education":"博士"}',
        '{"graduationDate":"2025-02-30"}',
        '{"graduationDate":"2025-06-20"}',
        '{"socialInsuranceMonths":-1}',
        '{"city":"苏州市","policyId":"forbidden"}',
        '{"eligibility":"PASS"}',
    ],
)
def test_invalid_or_overreaching_llm_output_is_rejected_as_a_whole(response: str) -> None:
    with pytest.raises(ProfileExtractionError):
        message = "2025年6月毕业" if response == '{"graduationDate":"2025-06-20"}' else "我在苏州，本科"
        asyncio.run(LLMProfileExtractor(StructuredProvider(response)).extract(message, UserProfile()))


def test_llm_patch_overlays_rule_patch_without_dropping_rule_only_fields() -> None:
    store = InMemorySessionStore()
    service = ChatService(
        StructuredProvider('{"education":"本科"}'),
        store,
        WorkflowAgent.default(),
        profile_extractor=LLMProfileExtractor(StructuredProvider('{"education":"本科"}')),
    )
    request = ChatRequest(
        sessionId="llm-overlay-session",
        userId="llm-overlay-user",
        message="我在苏州，社保交了12个月",
        userProfile=UserProfile(),
    )

    state = asyncio.run(service._run_workflow(request))

    assert state.userProfile.city == "苏州市"
    assert state.userProfile.education == "本科"
    assert state.userProfile.socialInsuranceMonths == 12


def test_invalid_llm_output_falls_back_to_complete_rule_patch() -> None:
    store = InMemorySessionStore()
    service = ChatService(
        StructuredProvider("not-json"),
        store,
        WorkflowAgent.default(),
        profile_extractor=LLMProfileExtractor(StructuredProvider("not-json")),
    )
    request = ChatRequest(
        sessionId="llm-fallback-session",
        userId="llm-fallback-user",
        message="我在苏州，本科，2025年毕业",
        userProfile=UserProfile(),
    )

    state = asyncio.run(service._run_workflow(request))

    assert state.userProfile.city == "苏州市"
    assert state.userProfile.education == "本科"
    assert state.userProfile.graduationYear == 2025


def test_latest_llm_extraction_overrides_historical_profile_without_cross_session_leakage() -> None:
    store = InMemorySessionStore()
    asyncio.run(store.set_internal_profile("correction-session", "user", UserProfile(employmentStatus="待就业")))
    service = ChatService(
        StructuredProvider('{"employmentStatus":"已就业"}'),
        store,
        WorkflowAgent.default(),
        profile_extractor=LLMProfileExtractor(StructuredProvider('{"employmentStatus":"已就业"}')),
    )
    state = asyncio.run(service._run_workflow(ChatRequest(
        sessionId="correction-session", userId="user", message="之前说错了，我已经就业了", userProfile=UserProfile(),
    )))

    assert state.userProfile.employmentStatus == "已就业"
    assert asyncio.run(store.get_internal_profile("other-session", "user")).employmentStatus is None


def test_provider_exception_falls_back_to_rule_patch() -> None:
    store = InMemorySessionStore()
    service = ChatService(
        StructuredProvider(RuntimeError("timeout")),
        store,
        WorkflowAgent.default(),
        profile_extractor=LLMProfileExtractor(StructuredProvider(RuntimeError("timeout"))),
    )

    state = asyncio.run(service._run_workflow(ChatRequest(
        sessionId="exception-fallback-session", userId="user", message="我在苏州，本科，2025年毕业", userProfile=UserProfile(),
    )))

    assert state.userProfile.model_dump(exclude_none=True) == {
        "city": "苏州市", "education": "本科", "graduationYear": 2025, "fields": [],
    }


def test_enabled_extractor_keeps_rule_fields_and_accumulates_four_turns() -> None:
    provider = RoutedStructuredProvider([
        "{}",
        '{"education":"本科"}',
        "{}",
        '{"entrepreneurshipIntent":false,"jobSeekingIntent":true}',
    ])
    settings = Settings(
        llm_base_url="https://example.invalid", llm_api_key="test-key", llm_model="test", llm_timeout_seconds=1,
        llm_max_tokens=128, llm_temperature=0, cors_origins=("http://localhost:5173",),
        session_history_limit=20, session_limit=20, profile_extraction_enabled=True,
    )
    client = TestClient(create_app(settings, provider))
    session_id = "enabled-extractor-turns"
    request = lambda message: {"sessionId": session_id, "userId": "user", "message": message, "userProfile": {}}

    client.post("/api/agent/chat", json=request("我是今年毕业生，想了解本地就业补贴"))
    client.post("/api/agent/chat", json=request("我在苏州，本科，2025年6月毕业，目前未就业"))
    client.post("/api/agent/chat", json=request("我已经连续缴纳社保12个月"))
    fourth = client.post("/api/agent/chat", json=request("我不创业，只想找工作")).json()["data"]
    profile = asyncio.run(client.app.state.chat_service._store.get_internal_profile(session_id, "user"))

    assert profile.city == "苏州市"
    assert profile.education == "本科"
    assert profile.graduationYear == 2025
    assert profile.employmentStatus == "待就业"
    assert profile.unemploymentStatus == "未就业"
    assert profile.socialInsuranceMonths == 12
    assert profile.entrepreneurshipIntent is False
    assert profile.jobSeekingIntent is True
    assert {item["policyId"] for item in fourth["policies"]}.isdisjoint({
        "suzhou-startup-one-time-2023", "suzhou-startup-social-2021",
    })
    assert sum(call[0]["content"].startswith("你是用户画像信息抽取器") for call in provider.calls) == 4


def test_unconfigured_provider_uses_rule_parser_without_failing_chat() -> None:
    settings = Settings(
        llm_base_url="https://example.invalid", llm_api_key="", llm_model="test", llm_timeout_seconds=1,
        llm_max_tokens=128, llm_temperature=0, cors_origins=("http://localhost:5173",),
        session_history_limit=20, session_limit=20, profile_extraction_enabled=True,
    )
    client = TestClient(create_app(settings))
    response = client.post("/api/agent/chat", json={
        "sessionId": "unconfigured-extractor-session", "userId": "user",
        "message": "我在苏州，本科，2025年毕业", "userProfile": {},
    })
    profile = asyncio.run(client.app.state.chat_service._store.get_internal_profile("unconfigured-extractor-session", "user"))

    assert response.status_code == 200
    assert profile.city == "苏州市"
    assert profile.education == "本科"
    assert profile.graduationYear == 2025
