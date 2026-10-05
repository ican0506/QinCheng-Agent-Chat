from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
import json
import logging
from time import perf_counter
from typing import Literal
import asyncio

from app.agent.models import GovernmentAgentState
from app.agent.presentation import PresentationAdapter
from app.realtime_policy.models import RealtimeSearchStatus
from app.agent.workflow import WorkflowAgent
from app.models.chat import ChatData, ChatRequest, UserProfile, WebSource
from app.core.errors import LLMServiceError
from app.services.llm.base import LLMMessage, LLMProvider
from app.stores.session_store import InMemorySessionStore
from app.services.profile_update_parser import ProfileUpdateParser
from app.services.llm_profile_extractor import LLMProfileExtractor, ProfileExtractionError
from app.services.policy_query_context import (
    PolicyDomainIntent,
    PolicyDomainIntentDetector,
    PolicyQueryContextResolver,
    UserGoal,
)
from app.policy.repository import PolicyRepository
from app.services.final_explanation_policy import (
    FinalExplanationDecision,
    FinalExplanationPolicy,
    FinalExplanationSkipReason,
)
from app.services.agent_reply_engine import (
    AgentReplyEngine,
    AgentReplyOutcome,
    AgentReplyPolicy,
)
from app.services.model_context import ModelContextBuilder, QINGCHENG_SYSTEM_PROMPT


logger = logging.getLogger(__name__)
timing_logger = logging.getLogger("uvicorn.error")

EDITABLE_PROFILE_FIELDS = frozenset({
    "city",
    "residencyRegistration",
    "education",
    "graduationYear",
    "graduationMonth",
    "employmentStatus",
    "flexibleEmploymentInsurance",
    "entrepreneurshipIntent",
})


# 兼容既有测试和外部引用；实际消息由 ModelContextBuilder 构造。
SYSTEM_PROMPT = QINGCHENG_SYSTEM_PROMPT


@dataclass(frozen=True)
class ChatStreamEvent:
    kind: Literal["delta", "done"]
    text: str = ""
    data: ChatData | None = None


@dataclass
class RequestTimings:
    profile_extraction_ms: float = 0
    workflow_ms: float = 0
    realtime_search_ms: float = 0
    material_updated: bool = False
    profile_extraction_calls: int = 0
    final_explanation_calls: int = 0
    agent_reply_rounds: int = 0
    agent_tool_calls: int = 0


class ChatService:
    def __init__(self, provider: LLMProvider, store: InMemorySessionStore, workflow_agent: WorkflowAgent, profile_extractor: LLMProfileExtractor | None = None, current_date: date | None = None, policy_repository: PolicyRepository | None = None, final_explanation_timeout_seconds: float = 12, reply_engine: AgentReplyEngine | None = None, model_context_builder: ModelContextBuilder | None = None) -> None:
        self._provider = provider
        self._store = store
        self._workflow_agent = workflow_agent
        self._profile_extractor = profile_extractor
        self._current_date = current_date
        self._policy_repository = policy_repository
        self._final_explanation_timeout_seconds = final_explanation_timeout_seconds
        self._reply_engine = reply_engine
        self._model_context_builder = model_context_builder or ModelContextBuilder()

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        return await self._store.delete_session(session_id, user_id)

    async def update_session_profile(
        self, session_id: str, user_id: str, submitted_profile: UserProfile
    ) -> ChatData:
        """保存用户手动确认的画像，并仅基于当前会话重新运行既有工作流。"""
        patch = {
            field: getattr(submitted_profile, field)
            for field in submitted_profile.model_fields_set
            if field in EDITABLE_PROFILE_FIELDS
        }
        if "city" in patch and patch["city"] in {"苏州", "苏州市"}:
            patch["city"] = "苏州市"
        if "residencyRegistration" in patch and patch["residencyRegistration"] in {"昆山户籍", "昆山市户籍", "苏州户籍", "苏州市户籍"}:
            patch["residencyRegistration"] = "本市户籍"
        # unemploymentStatus 是资格规则使用的内部派生字段。手工更新就业状态时
        # 必须同步它，避免先前聊天提取出的“未就业”继续参与后续判断。
        if patch.get("employmentStatus") == "待就业":
            patch["unemploymentStatus"] = "未就业"
        elif "employmentStatus" in patch:
            patch["unemploymentStatus"] = None
        profile = await self._store.update_manual_profile(session_id, user_id, patch)
        declarations = await self._store.get_material_declarations(session_id, user_id)
        previous_query = await self._store.get_policy_query_context(session_id, user_id)
        workflow_message = previous_query or "更新个人画像"
        state = await self._execute_workflow(
            session_id=session_id,
            message=workflow_message,
            user_profile=profile,
            material_declarations=declarations,
            policy_search_query=previous_query or workflow_message,
            active_goal=await self._store.get_user_goal(session_id, user_id),
            requested_goal=await self._store.get_user_goal(session_id, user_id),
        )
        await self._store.set_material_declarations(session_id, user_id, state.materialDeclarations)
        await self._store.set_internal_profile(session_id, user_id, state.userProfile)
        request = ChatRequest(
            sessionId=session_id,
            userId=user_id,
            message=workflow_message,
            userProfile=UserProfile(),
        )
        return self._result(request, state, self._fallback_reply(state))

    async def _messages(
        self, request: ChatRequest, state: GovernmentAgentState
    ) -> tuple[str, list[LLMMessage]]:
        history = await self._store.get_messages(request.sessionId, request.userId)
        _, messages = self._model_context_builder.final_messages(state, history)
        return request.message.strip(), messages

    @staticmethod
    def _result(
        request: ChatRequest,
        state: GovernmentAgentState,
        reply: str,
        sources: list[WebSource] | None = None,
    ) -> ChatData:
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
            sources=sources or [],
            suggestedActions=[
                {"label": action.label, "prompt": action.prompt}
                for action in state.suggestedActions
            ],
            applicationGuide=state.applicationGuide,
        )

    @staticmethod
    def _fallback_reply(
        state: GovernmentAgentState,
        decision: FinalExplanationDecision | None = None,
    ) -> str:
        local_reply = state.finalReply or PresentationAdapter.fallback_reply(state)
        if decision and decision.skip_reason is FinalExplanationSkipReason.MATERIAL_UPDATE:
            local_reply = "已记录您本轮更新的材料准备情况。\n\n" + local_reply
        return local_reply

    @staticmethod
    def _realtime_reply(state: GovernmentAgentState) -> str:
        status = state.realtimeSearchStatus
        if status is RealtimeSearchStatus.NOT_TRIGGERED:
            return ''
        if status is RealtimeSearchStatus.DISABLED:
            return '未配置实时检索服务，本次结果基于本地已核验政策库。'
        if status in {RealtimeSearchStatus.TIMEOUT, RealtimeSearchStatus.ERROR}:
            return '实时官方信息暂时无法检索，本次结果基于本地已核验政策库。'
        if status is RealtimeSearchStatus.NO_RESULTS:
            return '已完成实时查询，当前未从已配置的官方来源中发现新的相关公开通知。'
        lines = ['官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。']
        for hit in state.realtimePolicyHits:
            if not hit.official:
                continue
            lines.append(hit.title)
            if hit.publishedAt:
                lines.append('发布时间：' + hit.publishedAt.isoformat())
            lines.append('官方来源：' + hit.url)
            if hit.relatedPolicyId is None:
                lines.append('发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。')
            else:
                lines.append('该证据与本地政策存在可靠关联；网页内容未覆盖本地资格规则，更新内容仍需人工核验。')
        return '\n'.join(lines)

    @staticmethod
    def _local_fallback_reply(state: GovernmentAgentState) -> str:
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            return "当前助手主要支持高校毕业生就业创业政策咨询，暂不提供该主题的解答。"
        historical_or_closed_notice = ChatService._historical_or_closed_notice(state)
        if historical_or_closed_notice is not None:
            return historical_or_closed_notice
        if state.userGoal is UserGoal.POLICY_FACT:
            if not state.candidatePolicies and not state.knowledgeEvidences:
                return "暂未在本地已核验政策库中找到与该问题高度相关的政策。"
            lines = ["已找到以下政策资料："]
            for candidate in state.candidatePolicies:
                lines.append(f"《{candidate.name}》")
                if candidate.conditions:
                    lines.append("申请条件：" + "；".join(candidate.conditions))
                if candidate.requiredMaterials:
                    lines.append("申请材料：" + "；".join(candidate.requiredMaterials))
                lines.append("官方来源：" + candidate.sourceUrl)
                notice = state.policyReferenceNotices.get(candidate.policyId)
                if notice:
                    lines.append("时效提示：" + notice)
            for evidence in state.knowledgeEvidences:
                lines.append(f"《{evidence.policyName}》")
                lines.append(evidence.chunkText)
                lines.append("官方来源：" + evidence.sourceUrl)
                lines.append("时效提示：" + ChatService._knowledge_currentness_notice(evidence.currentness))
            lines.append("以上为政策事实说明，不代表对您个人资格的判断。")
            return "\n".join(lines)
        if state.knowledgeEvidences and not state.candidatePolicies:
            evidence = state.knowledgeEvidences[0]
            reply = (
                f"已找到《{evidence.policyName}》的官方资料，但该政策目前尚未进入结构化资格规则库，"
                "因此不能自动进行资格判定。\n"
                f"官方来源：{evidence.sourceUrl}\n"
                "时效提示：" + ChatService._knowledge_currentness_notice(evidence.currentness)
            )
            if state.needFollowUp and state.followUpQuestions:
                reply += "\n还需要补充：" + "；".join(state.followUpQuestions)
            return reply
        if state.userGoal is UserGoal.JOB_SEARCH:
            policy_names = "、".join(policy.name for policy in state.candidatePolicies[:2])
            reply = (
                f"如果你的目标是尽快找工作，当前更值得优先关注{policy_names or '就业服务和高校毕业生就业支持'}。"
                "我会先按就业方向为你提供信息；如果你之后想判断某项补贴资格，再补充该政策真正需要的信息。"
            )
        elif state.userGoal is UserGoal.POLICY_DISCOVERY:
            policy_names = "、".join(policy.name for policy in state.candidatePolicies[:3])
            reply = (
                f"根据你目前提供的信息，先为你整理更相关的方向：{policy_names or '高校毕业生就业创业支持'}。"
                "如需判断某一项是否符合，我再针对该政策确认必要信息。"
            )
        elif state.userGoal is UserGoal.APPLICATION_GUIDE:
            if not state.candidatePolicies:
                reply = "暂未找到对应政策资料；请补充想办理的政策名称，我再为你整理官方流程。"
            else:
                policy = state.candidatePolicies[0]
                parts = [f"《{policy.name}》通常可按以下流程了解和办理："]
                if policy.process:
                    parts.append("办理流程：" + "；".join(policy.process))
                if policy.requiredMaterials:
                    parts.append("参考材料：" + "；".join(policy.requiredMaterials))
                parts.append("官方来源：" + policy.sourceUrl)
                parts.append("具体材料和受理要求请以当前官方办事指南为准。")
                reply = "\n".join(parts)
        elif state.needFollowUp and state.followUpQuestions:
            reply = "要判断你是否符合当前政策，还需要确认：" + "；".join(state.followUpQuestions)
        else:
            statuses = {item.overallStatus.value for item in state.eligibilityResults if item.policyId not in state.policyReferenceNotices}
            if "MANUAL_REVIEW" in statuses:
                reply = "部分条件需要经办机构或人工进一步核验，请查看右侧工作台中的核验项、材料清单和办理步骤。"
            elif "PASS" in statuses:
                reply = "已匹配相关政策，并完成资格辅助判断和办理路径规划。请查看右侧工作台中的政策依据、材料清单和办理步骤。"
            elif not state.candidatePolicies:
                reply = "暂未找到与当前信息高度相关的政策，可以补充地区、毕业时间或就业创业情况后继续查询。"
            else:
                reply = "已完成政策匹配和初步资格辅助判断，请查看右侧工作台了解具体结果。"
        # 混合召回时，历史/关闭状态由政策卡片呈现；不要把某条候选的时效说明
        # 追加为对话的第二段，避免用户把历史通知误读成当前任务的行动建议。
        # 全部候选都是历史/关闭记录时，函数开头的 `_historical_or_closed_notice` 已处理。
        return reply

    @staticmethod
    def _knowledge_currentness_notice(currentness: str) -> str:
        if currentness == "HISTORICAL":
            return "该资料属于历史政策或历史通知，不能据此认为当前仍开放。"
        if currentness == "UNKNOWN":
            return "当前有效性尚未完成结构化确认，办理前应以最新官方通知为准。"
        return "该资料标记为当前政策资料，仍需以官方办理要求为准。"

    @staticmethod
    def _historical_or_closed_notice(state: GovernmentAgentState) -> str | None:
        # 只有全部候选都属于历史/关闭参考，才采用整轮历史回复。
        if state.candidatePolicies and all(p.policyId in state.policyReferenceNotices for p in state.candidatePolicies):
            if len(state.candidatePolicies) == 1:
                return state.policyReferenceNotices[state.candidatePolicies[0].policyId]
            return "\n\n".join(f"《{p.name}》：{state.policyReferenceNotices[p.policyId]}" for p in state.candidatePolicies)
        return None

    @staticmethod
    def _may_use_llm_reply(state: GovernmentAgentState, reply: str) -> bool:
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE or state.policyReferenceNotices:
            return False
        if state.candidatePolicies or state.needFollowUp:
            return bool(state.candidatePolicies) and not state.needFollowUp
        return not any(term in reply for term in ("补贴", "见习", "贷款", "创业社会保险"))

    async def _agent_reply(
        self, request: ChatRequest, state: GovernmentAgentState, timings: RequestTimings
    ) -> AgentReplyOutcome | None:
        """Agent 自主回复引擎；未启用、不适用或失败时返回 None（调用方回退原有路径）。"""
        if self._reply_engine is None or not self._provider.supports_tools:
            return None
        if not AgentReplyPolicy.decide(state, material_updated=timings.material_updated):
            return None
        timings.final_explanation_calls = 1
        try:
            history = await self._store.get_messages(request.sessionId, request.userId)
            outcome = await self._reply_engine.generate(request, state, history)
        except Exception:
            logger.warning("agent_reply_failed trace fallback to deterministic reply", exc_info=True)
            return None
        timings.agent_reply_rounds = outcome.tool_rounds
        timings.agent_tool_calls = outcome.tool_calls
        return outcome

    async def _run_workflow(
        self, request: ChatRequest, timings: RequestTimings | None = None
    ) -> GovernmentAgentState:
        metrics = timings or RequestTimings()
        declarations = await self._store.get_material_declarations(request.sessionId, request.userId)
        stored_profile = await self._store.get_internal_profile(request.sessionId, request.userId)
        previous_query = await self._store.get_policy_query_context(request.sessionId, request.userId)
        query_context, search_query = PolicyQueryContextResolver.resolve(request.message, previous_query)
        previous_goal = await self._store.get_user_goal(request.sessionId, request.userId)
        await self._store.set_policy_query_context(request.sessionId, request.userId, query_context)
        # 域外消息不需要画像抽取；具体目标解析与最终路由仍只由图中的
        # GoalResolver/conditional edge 完成。
        if PolicyDomainIntentDetector.detect(request.message) is PolicyDomainIntent.OUT_OF_SCOPE:
            state = await self._execute_workflow(
                session_id=request.sessionId,
                message=request.message.strip(),
                user_profile=stored_profile,
                material_declarations=declarations,
                policy_search_query=search_query,
                metrics=metrics,
                active_goal=previous_goal,
            )
            await self._store.set_internal_profile(request.sessionId, request.userId, state.userProfile)
            return state
        manual_fields = await self._store.get_manual_profile_fields(request.sessionId, request.userId)
        request_values = {
            name: getattr(request.userProfile, name)
            for name in request.userProfile.__class__.model_fields
            if getattr(request.userProfile, name) is not None and name not in manual_fields
        }
        rule_patch = ProfileUpdateParser.parse(request.message, current_date=self._current_date)
        llm_patch: dict[str, object] = {}
        extraction_source = "rule"
        fallback_reason: str | None = None
        if self._profile_extractor is not None:
            started_at = perf_counter()
            metrics.profile_extraction_calls = 1
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
            metrics.profile_extraction_ms = (perf_counter() - started_at) * 1000
        else:
            logger.info("profile_extraction source=rule extracted_fields=%s fallback_reason=%s", sorted(rule_patch), None)
        graduation_date_patch = ProfileUpdateParser.graduation_date_overrides(request.message)
        relative_time_patch = ProfileUpdateParser.relative_time_overrides(
            request.message, current_date=self._current_date
        )
        deterministic_intent_patch = ProfileUpdateParser.deterministic_intent_overrides(
            request.message
        )
        current_rule_patch = {
            **rule_patch,
            # LLM 只补足自然语言字段；明确的日期、意图、参保和就业纠正规则必须最后生效。
            **llm_patch,
            **graduation_date_patch,
            **relative_time_patch,
            **deterministic_intent_patch,
            **ProfileUpdateParser.flexible_insurance_overrides(request.message),
            **ProfileUpdateParser.employment_status_overrides(request.message),
        }
        # 手动值阻止陈旧客户端快照覆盖；本轮明确解析到的消息始终可以纠正手动值。
        await self._store.clear_manual_profile_fields(
            request.sessionId, request.userId, set(current_rule_patch) | set(llm_patch)
        )
        profile = stored_profile.model_copy(
            update={
                **request_values,
                **current_rule_patch,
            }
        )
        state = await self._execute_workflow(
            session_id=request.sessionId,
            message=request.message.strip(),
            user_profile=profile,
            material_declarations=declarations,
            policy_search_query=search_query,
            metrics=metrics,
            active_goal=previous_goal,
        )
        await self._store.set_user_goal(
            request.sessionId,
            request.userId,
            None if state.userGoal is UserGoal.OUT_OF_SCOPE else state.activeGoal,
        )
        await self._store.set_material_declarations(request.sessionId, request.userId, state.materialDeclarations)
        await self._store.set_internal_profile(request.sessionId, request.userId, state.userProfile)
        return state

    async def _execute_workflow(
        self,
        session_id: str,
        message: str,
        user_profile: UserProfile,
        material_declarations: dict[str, bool],
        policy_search_query: str | None,
        metrics: RequestTimings | None = None,
        active_goal: UserGoal | None = None,
        requested_goal: UserGoal | None = None,
    ) -> GovernmentAgentState:
        workflow_started_at = perf_counter()
        workflow_timings: dict[str, float] = {}
        state = await self._workflow_agent.run(
            session_id=session_id,
            message=message,
            user_profile=user_profile,
            material_declarations=material_declarations,
            policy_search_query=policy_search_query,
            timings=workflow_timings,
            user_goal=requested_goal,
            active_goal=active_goal,
        )
        if metrics is not None:
            metrics.workflow_ms = (perf_counter() - workflow_started_at) * 1000
            metrics.realtime_search_ms = workflow_timings.get("realtime_search_ms", 0)
            metrics.material_updated = state.materialDeclarations != material_declarations
        return state

    @staticmethod
    def _log_request_timing(
        trace_id: str | None,
        timings: RequestTimings,
        decision: FinalExplanationDecision,
        final_explanation_ms: float,
        total_ms: float,
    ) -> None:
        timing_logger.info(
            "agent_request_timing trace_id=%s profile_extraction_ms=%d workflow_ms=%d "
            "final_explanation_ms=%d realtime_search_ms=%d request_total_ms=%d "
            "final_explanation_skipped=%s skip_reason=%s profile_extraction_calls=%d "
            "final_explanation_calls=%d agent_reply_rounds=%d agent_tool_calls=%d",
            trace_id or "-",
            timings.profile_extraction_ms,
            timings.workflow_ms,
            final_explanation_ms,
            timings.realtime_search_ms,
            total_ms,
            not decision.generate,
            decision.skip_reason.value,
            timings.profile_extraction_calls,
            timings.final_explanation_calls,
            timings.agent_reply_rounds,
            timings.agent_tool_calls,
        )

    async def chat(self, request: ChatRequest, trace_id: str | None = None) -> ChatData:
        request_started_at = perf_counter()
        timings = RequestTimings()
        state = await self._run_workflow(request, timings)
        decision = FinalExplanationPolicy.decide(state, material_updated=timings.material_updated)
        user_message = request.message.strip()
        reply = self._fallback_reply(state, decision)
        explanation_started_at = perf_counter()
        outcome = await self._agent_reply(request, state, timings)
        if outcome is not None:
            reply = outcome.reply
            realtime_reply = self._realtime_reply(state)
            if realtime_reply and state.realtimeSearchStatus is not RealtimeSearchStatus.DISABLED:
                reply += "\n\n" + realtime_reply
        elif decision.generate:
            timings.final_explanation_calls = 1
            try:
                _, messages = await self._messages(request, state)
                generated = await asyncio.wait_for(
                    self._provider.complete(messages),
                    timeout=self._final_explanation_timeout_seconds,
                )
                if self._may_use_llm_reply(state, generated):
                    reply = generated
                    realtime_reply = self._realtime_reply(state)
                    if realtime_reply and state.realtimeSearchStatus is not RealtimeSearchStatus.DISABLED:
                        reply += "\n\n" + realtime_reply
            except Exception:
                pass
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        self._log_request_timing(
            trace_id, timings, decision,
            (perf_counter() - explanation_started_at) * 1000,
            (perf_counter() - request_started_at) * 1000,
        )
        return self._result(
            request, state, reply,
            sources=[WebSource(**source) for source in outcome.sources] if outcome else None,
        )

    async def stream_chat(self, request: ChatRequest, trace_id: str | None = None) -> AsyncIterator[ChatStreamEvent]:
        request_started_at = perf_counter()
        timings = RequestTimings()
        state = await self._run_workflow(request, timings)
        decision = FinalExplanationPolicy.decide(state, material_updated=timings.material_updated)
        user_message = request.message.strip()
        chunks: list[str] = []
        explanation_started_at = perf_counter()
        outcome = await self._agent_reply(request, state, timings)
        if outcome is not None:
            chunks = [outcome.reply]
            yield ChatStreamEvent(kind="delta", text=outcome.reply)
        elif decision.generate:
            timings.final_explanation_calls = 1
            try:
                _, messages = await self._messages(request, state)
                async with asyncio.timeout(self._final_explanation_timeout_seconds):
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
        reply = "".join(chunks).strip() or self._fallback_reply(state, decision)
        if chunks:
            realtime_reply = self._realtime_reply(state)
            if realtime_reply and state.realtimeSearchStatus is not RealtimeSearchStatus.DISABLED:
                reply += "\n\n" + realtime_reply
        await self._store.append_exchange(
            request.sessionId, request.userId, user_message, reply
        )
        self._log_request_timing(
            trace_id, timings, decision,
            (perf_counter() - explanation_started_at) * 1000,
            (perf_counter() - request_started_at) * 1000,
        )
        yield ChatStreamEvent(
            kind="done",
            data=self._result(
                request, state, reply,
                sources=[WebSource(**source) for source in outcome.sources] if outcome else None,
            ),
        )
