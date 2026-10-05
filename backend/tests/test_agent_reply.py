from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.base import AgentMessage, AgentToolCall, AgentToolResponse, LLMProvider


class ScriptedToolProvider(LLMProvider):
    """支持 function calling 的脚本化测试替身：按脚本依次返回工具调用或文本。"""

    def __init__(self, script: list[AgentToolResponse | Exception]) -> None:
        self._script = list(script)
        self.calls: list[list[AgentMessage]] = []
        self.tool_defs: list[list[dict[str, Any]]] = []

    @property
    def name(self) -> str:
        return "scripted-tool-provider"

    @property
    def supports_tools(self) -> bool:
        return True

    async def complete(self, messages) -> str:
        raise NotImplementedError("scripted tool provider only supports tools path")

    async def complete_with_tools(
        self, messages: list[AgentMessage], tools: list[dict[str, Any]]
    ) -> AgentToolResponse:
        self.calls.append([dict(message) for message in messages])
        self.tool_defs.append(tools)
        step = self._script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    @staticmethod
    def tool_call(name: str, arguments: str, call_id: str = "call-1") -> AgentToolResponse:
        return AgentToolResponse(tool_calls=[AgentToolCall(id=call_id, name=name, arguments=arguments)])

    @staticmethod
    def text(content: str) -> AgentToolResponse:
        return AgentToolResponse(content=content)


def tool_names(provider: ScriptedToolProvider) -> set[str]:
    if not provider.tool_defs:
        return set()
    return {item["function"]["name"] for item in provider.tool_defs[0]}


def settings(**overrides: object) -> Settings:
    values = dict(
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
    values.update(overrides)
    return Settings(**values)


COMPLETE_PROFILE = {
    "city": "苏州市",
    "education": "本科",
    "graduationYear": 2025,
    "graduationDate": "2025-06-20",
    "employmentStatus": "创业中",
    "socialInsuranceMonths": 12,
    "businessRegistrationMonths": 12,
}


def payload(message: str, profile: dict | None = None, session: str = "agent-reply-session") -> dict:
    return {
        "sessionId": session,
        "userId": "agent-reply-user",
        "message": message,
        "userProfile": profile or {},
    }


def test_agent_tool_call_produces_grounded_reply_and_feeds_tool_result_back() -> None:
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("search_policies", '{"query": "创业社会保险补贴"}'),
        ScriptedToolProvider.text("根据检索结果，《创业社会保险补贴》面向毕业5年内的高校毕业生创业者，连续缴纳社保满1年即可申请。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我符合创业社会保险补贴吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["replyText"].startswith("根据检索结果")
    assert "search_policies" in tool_names(provider)
    # 第二轮请求中包含第一轮的工具结果消息（role=tool）
    tool_messages = [message for message in provider.calls[1] if message.get("role") == "tool"]
    assert tool_messages and "创业社会保险补贴" in tool_messages[0]["content"]
    assert set(data) == {
        "sessionId", "replyText", "needFollowUp", "followUpQuestions", "userProfile",
        "policies", "eligibility", "plan", "materialResults", "sources", "suggestedActions", "applicationGuide",
    }


def test_agent_grounding_violation_falls_back_to_deterministic_template() -> None:
    provider = ScriptedToolProvider([
        ScriptedToolProvider.text("推荐您申请创业补贴，条件非常宽松，每月能领2000元。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我想咨询政策"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["needFollowUp"] is False
    assert "每月能领2000元" not in data["replyText"]
    assert data["suggestedActions"]


def test_agent_self_intro_with_generic_policy_terms_passes_grounding() -> None:
    """自我介绍提到"帮你查补贴"等泛词不算无来源推荐，不应误拒。"""
    provider = ScriptedToolProvider([
        ScriptedToolProvider.text(
            "我是苏州毕业生就业创业政策助手，可以帮你查询补贴政策、判断资格、梳理办理材料。"
            "想开始的话，先告诉我你所在的城市和毕业年份吧。"
        ),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("你是谁"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["replyText"].startswith("我是苏州毕业生就业创业政策助手")


def test_agent_tool_loop_limit_falls_back_to_template() -> None:
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("search_policies", '{"query": "就业补贴"}', f"call-{index}")
        for index in range(3)
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我符合创业社会保险补贴吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(provider.calls) == 3
    assert data["replyText"]
    assert data["policies"]


def test_agent_provider_failure_keeps_structured_result() -> None:
    provider = ScriptedToolProvider([RuntimeError("tool provider unavailable")])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我符合创业社会保险补贴吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["policies"]
    assert data["eligibility"]
    assert data["plan"]
    assert data["replyText"]


def test_agent_disabled_by_settings_keeps_legacy_single_call_path() -> None:
    class LegacyProvider(LLMProvider):
        def __init__(self) -> None:
            self.complete_calls = 0
            self.tool_calls = 0

        @property
        def name(self) -> str:
            return "legacy-provider"

        async def complete(self, messages) -> str:
            self.complete_calls += 1
            return "结构化政策结果的自然语言说明。"

    provider = LegacyProvider()
    client = TestClient(create_app(settings(agent_reply_enabled=False), provider))

    response = client.post("/api/agent/chat", json=payload(
        "我现在同时可能涉及哪些就业和创业政策？帮我比较一下", COMPLETE_PROFILE,
    ))

    assert response.status_code == 200
    assert provider.complete_calls == 1
    assert provider.tool_calls == 0
    assert response.json()["data"]["replyText"] == "结构化政策结果的自然语言说明。"


def test_out_of_scope_never_invokes_agent_provider() -> None:
    provider = ScriptedToolProvider([])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("周末哪里看电影？", COMPLETE_PROFILE))

    assert response.status_code == 200
    assert provider.calls == []
    assert response.json()["data"]["replyText"] == "当前助手主要支持高校毕业生就业创业政策咨询，暂不提供该主题的解答。"


def test_agent_grounding_allows_material_name_from_tool_result() -> None:
    """工具返回的材料/表单名（如《...申请表》）来自已核验数据源，引用时不得误拒。"""
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call("check_materials", '{"policy_id": "suzhou-startup-social-2021"}', "call-m1"),
        ScriptedToolProvider.text("您可以对照《苏州市创业社会保险补贴申请表》准备材料，该表可向经办窗口领取。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我符合创业社会保险补贴吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["replyText"].startswith("您可以对照")
    tool_messages = [message for message in provider.calls[1] if message.get("role") == "tool"]
    assert tool_messages and "苏州市创业社会保险补贴申请表" in tool_messages[0]["content"]


def test_agent_realtime_tool_reports_disabled_without_network() -> None:
    provider = ScriptedToolProvider([
        ScriptedToolProvider.tool_call(
            "search_realtime_policy",
            '{"query": "创业社会保险补贴 最新申报通知", "reason": "用户询问当前是否仍可申报"}',
        ),
        ScriptedToolProvider.text("实时官方检索当前未启用。本地已核验政策库中的《创业社会保险补贴》仍可作为政策依据参考。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("创业社会保险补贴现在还能申请吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    data = response.json()["data"]
    tool_messages = [message for message in provider.calls[1] if message.get("role") == "tool"]
    assert tool_messages and "DISABLED" in tool_messages[0]["content"]
    assert "《创业社会保险补贴》" in data["replyText"]


def test_agent_system_prompt_contains_current_date() -> None:
    """LLM 不知道今天日期，系统提示必须注入服务器当前日期，否则模型会编造日期。"""
    provider = ScriptedToolProvider([
        ScriptedToolProvider.text("根据结构化上下文，《创业社会保险补贴》面向毕业5年内的高校毕业生创业者。"),
    ])
    client = TestClient(create_app(settings(), provider))

    response = client.post("/api/agent/chat", json=payload("我符合创业社会保险补贴吗？", COMPLETE_PROFILE))

    assert response.status_code == 200
    system_message = next(message for message in provider.calls[0] if message.get("role") == "system")
    assert "当前日期：" in system_message["content"]
    assert "不得自行编造或推测日期" in system_message["content"]
