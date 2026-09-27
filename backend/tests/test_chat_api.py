from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import LLMTimeoutError
from app.main import create_app
from app.services.llm.base import LLMMessage, LLMProvider


class RecordingProvider(LLMProvider):
    def __init__(self, replies: list[str] | None = None) -> None:
        self.replies = replies or ["你好，我可以和你一起梳理问题。"]
        self.calls: list[list[LLMMessage]] = []

    @property
    def name(self) -> str:
        return "recording-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.calls.append([message.copy() for message in messages])
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


class TimeoutProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "timeout-test-provider"

    async def complete(self, messages: list[LLMMessage]) -> str:
        raise LLMTimeoutError()


class StreamingProvider(RecordingProvider):
    async def stream(self, messages: list[LLMMessage]):
        self.calls.append([message.copy() for message in messages])
        yield "第一段"
        yield "，第二段。"


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[6:].strip() for line in lines if line.startswith("event:"))
        data = next(line[5:].strip() for line in lines if line.startswith("data:"))
        events.append((event, json.loads(data)))
    return events


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


def payload(message: str = "你好") -> dict:
    return {
        "sessionId": "session-12345678",
        "userId": "user-1",
        "message": message,
        "userProfile": {
            "city": "杭州",
            "education": "本科",
            "graduationYear": 2026,
            "employmentStatus": "创业中",
        },
    }


def test_chat_returns_formal_contract_and_trace_id() -> None:
    provider = RecordingProvider()
    client = TestClient(create_app(settings(), provider))

    response = client.post(
        "/api/agent/chat",
        json=payload(),
        headers={"X-Trace-Id": "trace-from-client"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["traceId"] == "trace-from-client"
    assert body["data"] == {
        "sessionId": "session-12345678",
        "replyText": "你好，我可以和你一起梳理问题。",
        "needFollowUp": False,
        "followUpQuestions": [],
        "userProfile": {
            "userId": None,
            "city": "杭州",
            "education": "本科",
            "graduationYear": 2026,
            "employmentStatus": "创业中",
            "isFirstTimeEntrepreneur": None,
            "enterpriseRegisterDate": None,
            "socialInsuranceMonths": None,
            "housingStatus": None,
            "fields": [],
        },
        "policies": [
            {
                "policyId": "DEMO-STARTUP-001", "name": "毕业生创业补贴（Demo）", "region": "杭州", "department": "Demo 人社服务部门", "summary": "仅用于 Workflow Agent 演示的创业补贴政策。", "effectiveDate": "2026-01-01", "expiryDate": None, "sourceUrl": "https://example.invalid/demo/startup", "matchReason": "用户为应届毕业生且当前处于创业中。", "conditions": ["应届毕业生", "处于创业状态"], "requiredMaterials": ["身份证明", "毕业证明", "创业主体信息"], "process": ["准备材料", "提交申请", "等待审核"], "isMock": True,
            },
            {
                "policyId": "DEMO-RENT-002", "name": "创业场地补贴（Demo）", "region": "杭州", "department": "Demo 人社服务部门", "summary": "仅用于 Workflow Agent 演示的场地补贴政策。", "effectiveDate": "2026-01-01", "expiryDate": None, "sourceUrl": "https://example.invalid/demo/rent", "matchReason": "用户可能需要创业场地支持，但场地情况尚未提供。", "conditions": ["应届毕业生", "具备符合条件的创业场地"], "requiredMaterials": ["毕业证明", "场地租赁证明"], "process": ["补充场地信息", "提交申请", "等待审核"], "isMock": True,
            },
            {
                "policyId": "DEMO-SOCIAL-003", "name": "创业社保补贴（Demo）", "region": "杭州", "department": "Demo 人社服务部门", "summary": "仅用于 Workflow Agent 演示的社保补贴政策。", "effectiveDate": "2026-01-01", "expiryDate": None, "sourceUrl": "https://example.invalid/demo/social", "matchReason": "用户创业相关诉求与社保支持主题相关。", "conditions": ["应届毕业生", "社保缴费满 6 个月"], "requiredMaterials": ["毕业证明", "社保缴费记录"], "process": ["核验缴费记录", "提交申请", "等待审核"], "isMock": True,
            },
        ],
        "eligibility": [
            {"policyId": "DEMO-STARTUP-001", "overallStatus": "PASS", "conditionResults": [{"conditionId": "graduate", "description": "应届毕业生", "status": "PASS", "reason": "已提供毕业年份与学历。", "userEvidence": "2026", "policyEvidence": "Demo 条件：应届毕业生"}, {"conditionId": "startup", "description": "处于创业状态", "status": "PASS", "reason": "用户画像标记为创业中。", "userEvidence": "创业中", "policyEvidence": "Demo 条件：创业中"}], "missingFields": [], "summary": "Demo 判断：基本画像满足创业补贴演示条件。"},
            {"policyId": "DEMO-RENT-002", "overallStatus": "UNKNOWN", "conditionResults": [{"conditionId": "venue", "description": "具备符合条件的创业场地", "status": "UNKNOWN", "reason": "未提供场地或租赁情况。", "userEvidence": None, "policyEvidence": "Demo 条件：符合条件的创业场地"}], "missingFields": ["housingStatus"], "summary": "Demo 判断：缺少创业场地信息，需人工或补充信息确认。"},
            {"policyId": "DEMO-SOCIAL-003", "overallStatus": "FAIL", "conditionResults": [{"conditionId": "social-insurance", "description": "社保缴费满 6 个月", "status": "FAIL", "reason": "未提供满足要求的社保缴费月数。", "userEvidence": "未提供", "policyEvidence": "Demo 条件：社保缴费满 6 个月"}], "missingFields": [], "summary": "Demo 判断：当前画像不满足社保缴费时长演示条件。"},
        ],
        "plan": {"summary": "这是基于 Mock 政策和固定规则生成的演示办理计划，不代表真实政策结论。", "steps": [{"stepId": "prepare-startup", "title": "优先准备创业补贴申请", "description": "Demo 判断为 PASS，可先整理创业补贴的申请材料。", "policyIds": ["DEMO-STARTUP-001"], "requiredMaterials": ["身份证明", "毕业证明", "创业主体信息"]}, {"stepId": "confirm-venue", "title": "补充创业场地信息", "description": "场地补贴为 UNKNOWN，需要补充租赁或场地证明。", "policyIds": ["DEMO-RENT-002"], "requiredMaterials": ["场地租赁证明"]}, {"stepId": "review-social", "title": "暂不申请社保补贴", "description": "社保补贴 Demo 判断为 FAIL，满足缴费时长后再核验。", "policyIds": ["DEMO-SOCIAL-003"], "requiredMaterials": ["社保缴费记录"]}], "notes": ["所有政策均为 Demo 数据，请以当地官方发布为准。"], "isMock": True},
        "materialResults": [],
    }


def test_second_turn_sends_server_side_history_to_provider() -> None:
    provider = RecordingProvider(["第一轮回答", "第二轮回答"])
    client = TestClient(create_app(settings(), provider))

    assert client.post("/api/agent/chat", json=payload("第一轮问题")).status_code == 200
    assert client.post("/api/agent/chat", json=payload("那第二步呢？")).status_code == 200

    assert [(item["role"], item["content"]) for item in provider.calls[1][1:]] == [
        ("user", "第一轮问题"),
        ("assistant", "第一轮回答"),
        ("user", "那第二步呢？"),
    ]


def test_stream_chat_emits_chunks_and_saves_history() -> None:
    provider = StreamingProvider(["第二轮回答"])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat/stream", json=payload("第一轮问题"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["delta", "delta", "done"]
    assert events[0][1] == {"text": "第一段"}
    assert events[1][1] == {"text": "，第二段。"}
    assert events[2][1]["data"]["replyText"] == "第一段，第二段。"

    assert client.post("/api/agent/chat", json=payload("继续")).status_code == 200
    assert [(item["role"], item["content"]) for item in provider.calls[1][1:]] == [
        ("user", "第一轮问题"),
        ("assistant", "第一段，第二段。"),
        ("user", "继续"),
    ]


def test_invalid_request_uses_error_contract() -> None:
    provider = RecordingProvider()
    client = TestClient(create_app(settings(), provider))
    bad_payload = payload()
    del bad_payload["message"]

    response = client.post("/api/agent/chat", json=bad_payload)

    assert response.status_code == 400
    assert response.json()["code"] == 1001
    assert response.json()["data"] is None
    assert response.json()["traceId"]


def test_session_cannot_be_reused_by_another_user() -> None:
    provider = RecordingProvider()
    client = TestClient(create_app(settings(), provider))
    assert client.post("/api/agent/chat", json=payload()).status_code == 200
    other_user = payload("继续")
    other_user["userId"] = "user-2"

    response = client.post("/api/agent/chat", json=other_user)

    assert response.status_code == 400
    assert response.json()["code"] == 1001


def test_llm_timeout_uses_error_code_5002() -> None:
    client = TestClient(create_app(settings(), TimeoutProvider()))

    response = client.post("/api/agent/chat", json=payload())

    assert response.status_code == 504
    assert response.json()["code"] == 5002
    assert response.json()["data"] is None


def test_stream_timeout_uses_error_event() -> None:
    client = TestClient(create_app(settings(), TimeoutProvider()))

    response = client.post("/api/agent/chat/stream", json=payload())

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == 5002
    assert events[-1][1]["data"] is None


def test_health_never_exposes_api_key() -> None:
    provider = RecordingProvider()
    client = TestClient(create_app(settings(), provider))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["llmConfigured"] is True
    assert "key" not in response.text.lower()
    assert "test-key" not in response.text
