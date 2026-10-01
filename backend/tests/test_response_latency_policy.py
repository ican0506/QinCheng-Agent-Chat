from __future__ import annotations

import asyncio
import logging

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.base import LLMMessage, LLMProvider


class SpyProvider(LLMProvider):
    def __init__(self, *, delay: float = 0) -> None:
        self.complete_calls = 0
        self.stream_calls = 0
        self.delay = delay

    @property
    def name(self) -> str:
        return "latency-spy"

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.complete_calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return "结构化政策结果的自然语言说明。"

    async def stream(self, messages: list[LLMMessage]):
        self.stream_calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        yield "结构化政策结果的自然语言说明。"


def settings(**overrides: object) -> Settings:
    values = dict(
        llm_base_url="https://example.invalid",
        llm_api_key="key",
        llm_model="test",
        llm_timeout_seconds=30,
        llm_max_tokens=128,
        llm_temperature=0,
        cors_origins=("http://localhost:5173",),
        session_history_limit=20,
        session_limit=20,
        profile_extraction_enabled=False,
        final_explanation_timeout_seconds=0.01,
    )
    values.update(overrides)
    return Settings(**values)


def request(message: str, session: str, profile: dict | None = None) -> dict:
    return {
        "sessionId": session,
        "userId": "latency-user",
        "message": message,
        "userProfile": profile or {},
    }


COMPLETE_PROFILE = {
    "city": "苏州市",
    "education": "本科",
    "graduationYear": 2025,
    "graduationDate": "2025-06-20",
    "employmentStatus": "创业中",
    "socialInsuranceMonths": 12,
    "businessRegistrationMonths": 12,
}


def test_out_of_scope_and_follow_up_skip_final_explanation() -> None:
    provider = SpyProvider()
    client = TestClient(create_app(settings(), provider))

    outside = client.post("/api/agent/chat", json=request("周末哪里看电影？", "latency-outside"))
    follow_up = client.post("/api/agent/chat", json=request("我想了解苏州就业补贴", "latency-follow-up"))

    assert outside.status_code == follow_up.status_code == 200
    assert provider.complete_calls == 0
    assert follow_up.json()["data"]["needFollowUp"] is True


def test_request_timing_log_contains_all_stage_fields_and_skip_reason(caplog) -> None:
    provider = SpyProvider()
    client = TestClient(create_app(settings(), provider))

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = client.post(
            "/api/agent/chat",
            json=request("周末哪里看电影？", "latency-log"),
            headers={"X-Trace-Id": "latency-trace"},
        )

    assert response.status_code == 200
    summary = next(record.getMessage() for record in caplog.records if "agent_request_timing" in record.getMessage())
    for field in (
        "trace_id=latency-trace", "profile_extraction_ms=", "workflow_ms=",
        "final_explanation_ms=", "realtime_search_ms=", "request_total_ms=",
        "final_explanation_skipped=True", "skip_reason=OUT_OF_SCOPE",
        "profile_extraction_calls=0", "final_explanation_calls=0",
    ):
        assert field in summary


def test_historical_no_policy_and_material_update_skip_final_explanation() -> None:
    provider = SpyProvider()
    client = TestClient(create_app(settings(), provider))

    historical = client.post("/api/agent/chat", json=request(
        "我想看2026届求职创业补贴之前的申报通知",
        "latency-historical",
        {**COMPLETE_PROFILE, "employmentStatus": "待就业", "jobSeekingIntent": True, "hardshipIdentity": "低保家庭"},
    ))
    no_policy = client.post("/api/agent/chat", json=request(
        "我想了解杭州高校毕业生就业政策",
        "latency-no-policy",
        {**COMPLETE_PROFILE, "city": "杭州市", "employmentStatus": "待就业"},
    ))
    assert provider.complete_calls == 0
    initial = client.post("/api/agent/chat", json=request(
        "我想申请创业社会保险补贴", "latency-material", COMPLETE_PROFILE,
    ))
    calls_before_declaration = provider.complete_calls
    declared = client.post("/api/agent/chat", json=request(
        "我已经准备好《苏州市创业社会保险补贴申请表》", "latency-material",
    ))

    assert historical.status_code == no_policy.status_code == initial.status_code == declared.status_code == 200
    assert provider.complete_calls == calls_before_declaration
    assert next(item for item in declared.json()["data"]["materialResults"] if "申请表" in item["materialName"])["status"] == "READY"


def test_normal_policy_explanation_and_complex_comparison_call_once_each() -> None:
    provider = SpyProvider()
    client = TestClient(create_app(settings(), provider))

    normal = client.post("/api/agent/chat", json=request(
        "一次性创业补贴需要什么条件？", "latency-normal", COMPLETE_PROFILE,
    ))
    comparison = client.post("/api/agent/chat", json=request(
        "我现在同时可能涉及哪些就业和创业政策？帮我比较一下", "latency-comparison", COMPLETE_PROFILE,
    ))

    assert normal.status_code == comparison.status_code == 200
    assert provider.complete_calls == 2


def test_final_explanation_timeout_returns_structured_http_200_fallback() -> None:
    provider = SpyProvider(delay=0.05)
    client = TestClient(create_app(settings(final_explanation_timeout_seconds=0.001), provider))

    response = client.post("/api/agent/chat", json=request(
        "我现在同时可能涉及哪些就业和创业政策？帮我比较一下", "latency-timeout", COMPLETE_PROFILE,
    ))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["policies"]
    assert data["eligibility"]
    assert data["plan"]
    assert data["replyText"] != "结构化政策结果的自然语言说明。"
    assert provider.complete_calls == 1


def test_stream_final_explanation_timeout_emits_done_without_error() -> None:
    provider = SpyProvider(delay=0.05)
    client = TestClient(create_app(settings(final_explanation_timeout_seconds=0.001), provider))

    response = client.post("/api/agent/chat/stream", json=request(
        "我现在同时可能涉及哪些就业和创业政策？帮我比较一下", "latency-stream-timeout", COMPLETE_PROFILE,
    ))

    assert response.status_code == 200
    assert "event: done" in response.text
    assert "event: error" not in response.text
    assert provider.stream_calls == 1
