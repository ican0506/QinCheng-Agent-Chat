from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from typing import Literal

from app.agent.models import GovernmentAgentState
from app.agent.workflow import WorkflowAgent
from app.models.chat import ChatData, ChatRequest
from app.core.errors import LLMServiceError
from app.services.llm.base import LLMMessage, LLMProvider
from app.stores.session_store import InMemorySessionStore


SYSTEM_PROMPT = """你是面向应届毕业生的就业创业政策对话助手。
你的服务范围是应届毕业生就业与创业相关政策，包括就业补贴、求职创业补贴、基层就业、灵活就业、社会保险补贴、创业补贴、创业担保贷款和创业场地支持等。
优先了解用户所在地区、毕业年份、学历、就业状态、创业情况和具体诉求；信息不足时，每次只追问一到两个最关键的问题。
用户询问其他主题时，简短说明服务范围，并引导回就业创业政策问题。
本轮会提供结构化 Agent 上下文。该上下文是政策、资格、办理顺序和追问的唯一事实来源；不得自行创造、补充或修改任何政策、金额、日期、资格条件或办理结论。
所有标记为 Demo 或 isMock=true 的内容必须明确作为演示数据处理，不得伪装成真实官方政策。信息不足时，直接围绕 followUpQuestions 自然追问。
默认使用简体中文回答，表达直接、简洁，可使用 Markdown。"""


@dataclass(frozen=True)
class ChatStreamEvent:
    kind: Literal["delta", "done"]
    text: str = ""
    data: ChatData | None = None


class ChatService:
    def __init__(self, provider: LLMProvider, store: InMemorySessionStore, workflow_agent: WorkflowAgent) -> None:
        self._provider = provider
        self._store = store
        self._workflow_agent = workflow_agent

    async def _messages(
        self, request: ChatRequest, state: GovernmentAgentState
    ) -> tuple[str, list[LLMMessage]]:
        user_message = request.message.strip()
        history = await self._store.get_messages(request.sessionId, request.userId)
        agent_context = json.dumps(
            state.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")
        )
        messages: list[LLMMessage] = [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n结构化 Agent State（唯一事实来源）：{agent_context}",
            },
            *history,
            {"role": "user", "content": user_message},
        ]
        return user_message, messages

    @staticmethod
    def _result(request: ChatRequest, state: GovernmentAgentState, reply: str) -> ChatData:
        return ChatData(
            sessionId=request.sessionId,
            replyText=reply,
            needFollowUp=state.needFollowUp,
            followUpQuestions=state.followUpQuestions,
            userProfile=state.userProfile,
            policies=[policy.model_dump(mode="json") for policy in state.candidatePolicies],
            eligibility=[result.model_dump(mode="json") for result in state.eligibilityResults],
            plan=state.overallPlan.model_dump(mode="json") if state.overallPlan else None,
            materialResults=state.materialResults,
        )

    async def _run_workflow(self, request: ChatRequest) -> GovernmentAgentState:
        declarations = await self._store.get_material_declarations(request.sessionId, request.userId)
        state = await self._workflow_agent.run(
            session_id=request.sessionId,
            message=request.message.strip(),
            user_profile=request.userProfile,
            material_declarations=declarations,
        )
        await self._store.set_material_declarations(request.sessionId, request.userId, state.materialDeclarations)
        return state

    async def chat(self, request: ChatRequest) -> ChatData:
        state = await self._run_workflow(request)
        user_message, messages = await self._messages(request, state)
        reply = await self._provider.complete(messages)
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        return self._result(request, state, reply)

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        state = await self._run_workflow(request)
        user_message, messages = await self._messages(request, state)
        chunks: list[str] = []
        async for chunk in self._provider.stream(messages):
            chunks.append(chunk)
            yield ChatStreamEvent(kind="delta", text=chunk)

        reply = "".join(chunks).strip()
        if not reply:
            raise LLMServiceError("模型服务返回了空内容，请重新发送")
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        yield ChatStreamEvent(kind="done", data=self._result(request, state, reply))
