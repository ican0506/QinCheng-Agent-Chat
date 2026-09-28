from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from app.agent.models import AgentStage
from app.agent.tools.mock import MockPolicySearchTool
from app.agent.workflow import WorkflowAgent
from app.core.config import Settings
from app.main import create_app
from app.models.chat import UserProfile
from app.services.llm.base import LLMMessage, LLMProvider


class RecordingProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "recording-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        return "这是基于演示政策生成的说明。"

    async def stream(self, messages: list[LLMMessage]):
        yield "这是"
        yield "流式说明。"


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


def complete_profile() -> UserProfile:
    return UserProfile(
        city="杭州",
        education="本科",
        graduationYear=2026,
        employmentStatus="创业中",
    )


def real_profile() -> dict:
    return {
        "city": "苏州市",
        "education": "本科",
        "graduationYear": 2026,
        "graduationDate": "2025-06-30",
        "employmentStatus": "创业中",
        "socialInsuranceMonths": 6,
        "businessRegistrationMonths": 12,
    }


def payload(profile: dict) -> dict:
    return {
        "sessionId": "session-workflow-12345678",
        "userId": "user-workflow-1",
        "message": "我想了解毕业生创业相关支持。",
        "userProfile": profile,
    }


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[6:].strip() for line in lines if line.startswith("event:"))
        data = next(line[5:].strip() for line in lines if line.startswith("data:"))
        events.append((event, json.loads(data)))
    return events


def test_workflow_completes_with_three_demo_policies() -> None:
    state = asyncio.run(WorkflowAgent.default().run(
        session_id="session-workflow-12345678",
        message="我想创业，能申请什么支持？",
        user_profile=complete_profile(),
    ))

    assert state.stage is AgentStage.COMPLETED
    assert [policy.policyId for policy in state.candidatePolicies] == [
        "DEMO-STARTUP-001",
        "DEMO-RENT-002",
        "DEMO-SOCIAL-003",
    ]
    assert [result.overallStatus.value for result in state.eligibilityResults] == [
        "PASS",
        "UNKNOWN",
        "FAIL",
    ]
    assert state.overallPlan is not None
    assert state.overallPlan.steps


def test_missing_profile_stops_before_policy_search() -> None:
    search_tool = MockPolicySearchTool()
    agent = WorkflowAgent.default(policy_search_tool=search_tool)

    state = asyncio.run(agent.run(
        session_id="session-workflow-12345678",
        message="我想申请创业补贴。",
        user_profile=UserProfile(city="杭州"),
    ))

    assert state.stage is AgentStage.PROFILE_COLLECTING
    assert state.needFollowUp is True
    assert state.followUpQuestions
    assert search_tool.call_count == 0


def test_chat_api_returns_agent_structured_data() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))

    response = client.post("/api/agent/chat", json=payload(real_profile()))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["policies"]
    assert all(item["isMock"] is False for item in body["data"]["policies"])
    assert any(item["overallStatus"] == "PASS" for item in body["data"]["eligibility"])
    assert body["data"]["plan"]["steps"]


def test_missing_profile_api_returns_normal_follow_up() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))

    response = client.post("/api/agent/chat", json=payload({"city": "杭州"}))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["needFollowUp"] is True
    assert body["data"]["followUpQuestions"]
    assert body["data"]["policies"] == []


def test_stream_done_keeps_agent_structured_data() -> None:
    client = TestClient(create_app(settings(), RecordingProvider()))

    response = client.post(
        "/api/agent/chat/stream",
        json=payload(real_profile()),
    )

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["delta", "delta", "done"]
    done = events[-1][1]
    assert done["code"] == 0
    assert done["data"]["policies"]
    assert all(item["isMock"] is False for item in done["data"]["policies"])
    assert done["data"]["eligibility"]
    assert done["data"]["plan"]["steps"]
