from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
import logging
from time import perf_counter
from typing import Literal

from app.agent.models import GovernmentAgentState
from app.agent.workflow import WorkflowAgent
from app.models.chat import ChatData, ChatRequest
from app.core.errors import LLMServiceError
from app.services.llm.base import LLMMessage, LLMProvider
from app.stores.session_store import InMemorySessionStore
from app.services.profile_update_parser import ProfileUpdateParser
from app.services.llm_profile_extractor import LLMProfileExtractor, ProfileExtractionError


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是面向应届毕业生的就业创业政策对话助手。
你的服务范围是应届毕业生就业与创业相关政策，包括就业补贴、求职创业补贴、基层就业、灵活就业、社会保险补贴、创业补贴、创业担保贷款和创业场地支持等。
优先了解用户所在地区、毕业年份、学历、就业状态、创业情况和具体诉求；信息不足时，每次只追问一到两个最关键的问题。
用户询问其他主题时，简短说明服务范围，并引导回就业创业政策问题。
本轮会提供结构化 Agent 上下文。该上下文是政策、资格、办理顺序和追问的唯一事实来源；不得自行创造、补充或修改任何政策、金额、日期、资格条件或办理结论。
只能解释结构化 Agent State 中已有的候选政策、资格、材料与计划；不得推荐 State 中不存在的具体政策。信息不足时，直接围绕 followUpQuestions 自然追问。
默认使用简体中文回答，表达直接、简洁，可使用 Markdown。"""


@dataclass(frozen=True)
class ChatStreamEvent:
    kind: Literal["delta", "done"]
    text: str = ""
    data: ChatData | None = None


class ChatService:
    def __init__(self, provider: LLMProvider, store: InMemorySessionStore, workflow_agent: WorkflowAgent, profile_extractor: LLMProfileExtractor | None = None) -> None:
        self._provider = provider
        self._store = store
        self._workflow_agent = workflow_agent
        self._profile_extractor = profile_extractor

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

    @staticmethod
    def _fallback_reply(state: GovernmentAgentState) -> str:
        historical_or_closed_notice = ChatService._historical_or_closed_notice(state)
        if historical_or_closed_notice is not None:
            return historical_or_closed_notice
        if state.needFollowUp and state.followUpQuestions:
            return f"已完成初步政策分析，还需要补充以下信息后才能继续判断：{'；'.join(state.followUpQuestions)}"
        statuses = {item.overallStatus.value for item in state.eligibilityResults}
        if "MANUAL_REVIEW" in statuses:
            return "部分条件需要经办机构或人工进一步核验，请查看右侧工作台中的核验项、材料清单和办理步骤。"
        if "PASS" in statuses:
            return "已匹配相关政策，并完成资格辅助判断和办理路径规划。请查看右侧工作台中的政策依据、材料清单和办理步骤。"
        if not state.candidatePolicies:
            return "暂未找到与当前信息高度相关的政策，可以补充地区、毕业时间或就业创业情况后继续查询。"
        return "已完成政策匹配和初步资格辅助判断，请查看右侧工作台了解具体结果。"

    @staticmethod
    def _historical_or_closed_notice(state: GovernmentAgentState) -> str | None:
        historical = any(
            any(condition.conditionId == "policy-validity" for condition in result.conditionResults)
            for result in state.eligibilityResults
        )
        closed = any("申报窗口已关闭" in result.summary for result in state.eligibilityResults)
        if historical and closed:
            return "当前知识库中的该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。"
        if historical:
            return "当前知识库中的该记录为历史政策依据，不能直接作为当前申请依据。请关注苏州市人社部门后续发布的最新年度申报安排。"
        if closed:
            return "该政策当前申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。"
        return None

    @staticmethod
    def _may_use_llm_reply(state: GovernmentAgentState, reply: str) -> bool:
        if ChatService._historical_or_closed_notice(state) is not None:
            return False
        if state.candidatePolicies or state.needFollowUp:
            return bool(state.candidatePolicies) and not state.needFollowUp
        return not any(term in reply for term in ("补贴", "见习", "贷款", "创业社会保险"))

    async def _run_workflow(self, request: ChatRequest) -> GovernmentAgentState:
        declarations = await self._store.get_material_declarations(request.sessionId, request.userId)
        stored_profile = await self._store.get_internal_profile(request.sessionId, request.userId)
        request_values = {
            name: getattr(request.userProfile, name)
            for name in request.userProfile.__class__.model_fields
            if getattr(request.userProfile, name) is not None
        }
        rule_patch = ProfileUpdateParser.parse(request.message)
        llm_patch: dict[str, object] = {}
        extraction_source = "rule"
        fallback_reason: str | None = None
        if self._profile_extractor is not None:
            started_at = perf_counter()
            try:
                llm_patch = await self._profile_extractor.extract(request.message, stored_profile)
                extraction_source = "llm"
            except ProfileExtractionError as exc:
                extraction_source = "rule_fallback"
                fallback_reason = str(exc)
            logger.info(
                "profile_extraction source=%s extracted_fields=%s fallback_reason=%s duration_ms=%d",
                extraction_source,
                sorted(llm_patch),
                fallback_reason,
                (perf_counter() - started_at) * 1000,
            )
        else:
            logger.info("profile_extraction source=rule extracted_fields=%s fallback_reason=%s", sorted(rule_patch), None)
        profile = stored_profile.model_copy(update={**request_values, **rule_patch, **llm_patch})
        state = await self._workflow_agent.run(
            session_id=request.sessionId,
            message=request.message.strip(),
            user_profile=profile,
            material_declarations=declarations,
        )
        await self._store.set_material_declarations(request.sessionId, request.userId, state.materialDeclarations)
        await self._store.set_internal_profile(request.sessionId, request.userId, state.userProfile)
        return state

    async def chat(self, request: ChatRequest) -> ChatData:
        request_started_at = perf_counter()
        state = await self._run_workflow(request)
        user_message, messages = await self._messages(request, state)
        reply = self._fallback_reply(state)
        explanation_started_at = perf_counter()
        if not state.needFollowUp:
            try:
                generated = await self._provider.complete(messages)
                if self._may_use_llm_reply(state, generated):
                    reply = generated
            except Exception:
                pass
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        logger.info(
            "chat_timing final_explanation_ms=%d total_request_ms=%d",
            (perf_counter() - explanation_started_at) * 1000,
            (perf_counter() - request_started_at) * 1000,
        )
        return self._result(request, state, reply)

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        request_started_at = perf_counter()
        state = await self._run_workflow(request)
        user_message, messages = await self._messages(request, state)
        chunks: list[str] = []
        explanation_started_at = perf_counter()
        if not state.needFollowUp:
            try:
                async for chunk in self._provider.stream(messages):
                    chunks.append(chunk)
                generated = "".join(chunks).strip()
                if self._may_use_llm_reply(state, generated):
                    for chunk in chunks:
                        yield ChatStreamEvent(kind="delta", text=chunk)
                else:
                    chunks = []
            except Exception:
                chunks = []
        reply = "".join(chunks).strip() or self._fallback_reply(state)
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        logger.info(
            "chat_timing final_explanation_ms=%d total_request_ms=%d",
            (perf_counter() - explanation_started_at) * 1000,
            (perf_counter() - request_started_at) * 1000,
        )
        yield ChatStreamEvent(kind="done", data=self._result(request, state, reply))
