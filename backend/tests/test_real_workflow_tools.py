from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.base import LLMMessage, LLMProvider


class RecordingProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "real-workflow-tools-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        return "已根据结构化政策结果生成说明。"

    async def stream(self, messages: list[LLMMessage]):
        yield "结构化"
        yield "结果。"


def settings() -> Settings:
    return Settings(
        llm_base_url="https://example.invalid/v1",
        llm_api_key="test-key",
        llm_model="test-model",
        llm_timeout_seconds=1,
        llm_max_tokens=256,
        llm_temperature=0.2,
        cors_origins=("http://localhost:5173",),
        session_history_limit=40,
        session_limit=100,
    )


def payload(message: str, profile: dict) -> dict:
    return {
        "sessionId": "session-real-tools-12345678",
        "userId": "user-real-tools-1",
        "message": message,
        "userProfile": {
            "city": "苏州市",
            "education": "本科",
            "graduationYear": 2026,
            "employmentStatus": "创业中",
            **profile,
        },
    }


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[6:].strip() for line in lines if line.startswith("event:"))
        data = next(line[5:].strip() for line in lines if line.startswith("data:"))
        events.append((event, json.loads(data)))
    return events


def test_chat_api_uses_real_policy_repository_and_rule_eligibility() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))
    response = client.post("/api/agent/chat", json=payload("我想申请创业社会保险补贴", {
        "graduationDate": "2025-06-30",
        "socialInsuranceMonths": 12,
        "businessRegistrationMonths": 12,
    }))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["policies"]
    assert all(not item["policyId"].startswith("DEMO-") and item["isMock"] is False for item in data["policies"])
    assert any(item["policyId"] == "suzhou-startup-social-2021" and item["overallStatus"] == "PASS" for item in data["eligibility"])


def test_real_unknown_fields_become_bounded_follow_up_questions() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))
    response = client.post("/api/agent/chat", json=payload("我想申请创业社会保险补贴", {
        "businessRegistrationMonths": 12,
    }))

    assert response.status_code == 200
    data = response.json()["data"]
    assert any(item["overallStatus"] == "UNKNOWN" for item in data["eligibility"])
    assert data["needFollowUp"] is True
    assert data["followUpQuestions"]
    assert len(data["followUpQuestions"]) <= 2
    assert any("毕业日期" in question or "社保" in question for question in data["followUpQuestions"])


def test_historical_closed_notice_is_not_returned_as_current_pass() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))
    response = client.post("/api/agent/chat", json=payload("我想申请求职创业补贴", {
        "jobSeekingIntent": True,
        "hardshipIdentity": "低保家庭",
    }))

    assert response.status_code == 200
    result = next(item for item in response.json()["data"]["eligibility"] if item["policyId"] == "suzhou-job-seeking-subsidy-2026")
    assert result["overallStatus"] == "MANUAL_REVIEW"
    assert "申报窗口已关闭" in result["summary"]


def test_stream_done_keeps_real_chat_data_contract() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))
    response = client.post("/api/agent/chat/stream", json=payload("我想申请创业社会保险补贴", {
        "graduationDate": "2025-06-30",
        "socialInsuranceMonths": 12,
        "businessRegistrationMonths": 12,
    }))

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["delta", "delta", "done"]
    data = events[-1][1]["data"]
    assert set(data) == {"sessionId", "replyText", "needFollowUp", "followUpQuestions", "userProfile", "policies", "eligibility", "plan", "materialResults"}
    assert data["policies"]
    assert all(not policy["policyId"].startswith("DEMO-") for policy in data["policies"])
