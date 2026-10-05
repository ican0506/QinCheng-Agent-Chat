from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.agent.models import GovernmentAgentState
from app.agent.reply_tools import ReplyToolContext, ReplyToolRegistry
from app.models.chat import ChatRequest
from app.realtime_policy.models import RealtimeSearchStatus
from app.services.llm.base import AgentMessage, LLMProvider
from app.services.policy_query_context import PolicyDomainIntent, PolicyQueryMode

logger = logging.getLogger(__name__)

AGENT_REPLY_SYSTEM_PROMPT = """你是面向应届毕业生的就业创业政策对话 Agent。
你拥有可自主调用的只读工具：search_policies（检索已核验政策）、get_policy_detail（政策详情）、
check_eligibility（确定性资格核验）、check_materials（材料要求与声明状态）、search_realtime_policy（官方域名实时检索）。
当结构化 Agent State 不足以回答时，自主决定调用工具补充事实；能直接回答时不必调用工具。
工具结果是政策、金额、日期、资格结论的唯一事实来源；不得编造、推断或修饰任何政策事实。
资格状态只能来自 check_eligibility 或结构化上下文，不得自行得出 PASS/FAIL。
实时检索结果只是官方公开证据，不能转化为资格结论；引用实时信息必须附官方 URL。
围绕用户本轮的真实诉求组织回复：直接回应问题本身，先给结论再给依据，表达自然简洁，可使用 Markdown。"""

# 无候选政策时的推荐话术守卫：只拦截"具体推荐句式"与"编造金额标准"，
# 不再按"补贴"等泛词整句拒绝（自我介绍提到"帮你查补贴"属于正常表达）。
_RECOMMENDATION_PATTERN = re.compile(
    r"(建议您?|推荐您?|可以申请|可申请|建议申请|推荐申请)[^。；\n]{0,30}"
    r"(补贴|见习|贷款|创业社会保险)"
)
_INVENTED_AMOUNT_PATTERN = re.compile(r"(每月|一次性|最高|标准为|不超过)[^。；\n]{0,20}\d+\s*元")

_POLICY_NAME_PATTERN = re.compile(r"《(.+?)》")

_WEEKDAY_NAMES = ("一", "二", "三", "四", "五", "六", "日")


def current_date_directive() -> str:
    """服务器当前日期（Asia/Shanghai）。LLM 不知道今天几号，必须显式注入，否则会编造日期。"""
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        # 极简测试镜像可能没有系统 tzdata；日期提示不能因此中断 Chat / SSE 主链路。
        now = datetime.now()
    return (
        f"当前日期：{now.year}年{now.month}月{now.day}日 星期{_WEEKDAY_NAMES[now.isoweekday() - 1]}（Asia/Shanghai）。"
        "用户提及「今天/现在/最近/最新」等时间时一律以该日期为准；"
        "除此之外的时间信息（发布日期、截止日期等）只能来自工具结果或结构化上下文，不得自行编造或推测日期。"
    )


@dataclass
class AgentReplyOutcome:
    reply: str
    tool_rounds: int = 0
    tool_calls: int = 0
    grounded: bool = True
    used_tools: bool = False
    sources: list[dict[str, str]] = field(default_factory=list)


class AgentReplyError(Exception):
    """Agent 回复失败，调用方应回退确定性模板。"""


class AgentReplyPolicy:
    """决定本轮是否启用 Agent 自主回复引擎。

    OUT_OF_SCOPE、材料更新、历史/关闭政策通知保持确定性快速路径：
    它们不需要模型参与，且有明确的产品行为与测试约束。
    其余场景一律交给 Agent 引擎生成自然语言回复。
    """

    @staticmethod
    def decide(state: GovernmentAgentState, *, material_updated: bool = False) -> bool:
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            return False
        if material_updated:
            return False
        if state.candidatePolicies and state.policyReferenceNotices and all(
            policy.policyId in state.policyReferenceNotices
            for policy in state.candidatePolicies
        ):
            return False
        return True


def strategy_directive(state: GovernmentAgentState) -> str:
    """根据结构化状态生成本轮的场景化回复策略，实现不同场景灵活调整回复。"""
    directives: list[str] = []
    if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
        directives.append("用户话题超出就业创业政策服务范围：简短说明服务范围并引导回政策话题，不调用任何工具。")
    if state.queryMode is PolicyQueryMode.FACT_QUERY:
        directives.append(
            "用户询问的是政策本身的事实（不是个人资格）：直接给出政策条件、材料、官方来源等事实说明；"
            "即使画像不完整也要完整回答政策事实，结尾可自然邀请用户补充情况以获得个性化判断。"
        )
    else:
        directives.append(
            "用户关注的是个人资格与办理：结论先行，说明资格状态、缺失信息或后续动作；"
            "信息不足时围绕 followUpQuestions 自然追问，一次不超过两个问题，不要机械罗列。"
        )
    if state.needFollowUp and state.followUpQuestions:
        directives.append(
            "本轮需要补充信息才能继续个性化判断：用对话化语言追问 " + "、".join(state.followUpQuestions)
            + "；同时可以先给用户已能确定的政策事实，减少等待感。"
        )
    if state.candidatePolicies:
        names = "、".join(policy.name for policy in state.candidatePolicies)
        directives.append(f"本轮候选政策（唯一可引用的本地政策）：{names}。")
    else:
        directives.append("本轮没有命中的候选政策：不得推荐任何具体政策；如需事实可调用 search_policies。")
    if state.eligibilityResults:
        directives.append("结构化上下文已含资格核验结果：直接基于其 PASS/FAIL/UNKNOWN/MANUAL_REVIEW 结论解释，不要重复调用 check_eligibility，除非用户问题涉及上下文之外的政策。")
    if state.overallPlan and state.overallPlan.steps:
        directives.append("结构化上下文已含办理计划：概括关键步骤与状态，不改变步骤顺序与结论。")
    if state.realtimeSearchStatus is not RealtimeSearchStatus.NOT_TRIGGERED:
        if state.realtimePolicyHits:
            directives.append("结构化上下文含实时官方检索证据：引用时必须附标题与官方 URL；relatedPolicyId 为空的通知尚未结构化核验，不能说用户符合。")
        else:
            directives.append("本轮实时检索未获得有效结果：如实说明并回到本地已核验政策库的结论。")
    if state.userMessage:
        directives.append(f"用户本轮原话：{state.userMessage}")
    return "\n".join(directives)


class AgentReplyEngine:
    """有界 Agent 回复循环：LLM 自主调用只读工具后生成事实接地的自然语言回复。"""

    def __init__(
        self,
        provider: LLMProvider,
        registry: ReplyToolRegistry,
        *,
        timeout_seconds: float = 15.0,
        max_tool_rounds: int = 3,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._timeout_seconds = timeout_seconds
        self._max_tool_rounds = max_tool_rounds

    async def generate(
        self,
        request: ChatRequest,
        state: GovernmentAgentState,
        history: list[AgentMessage],
    ) -> AgentReplyOutcome:
        return await asyncio.wait_for(
            self._generate(request, state, history),
            timeout=self._timeout_seconds,
        )

    async def _generate(
        self,
        request: ChatRequest,
        state: GovernmentAgentState,
        history: list[AgentMessage],
    ) -> AgentReplyOutcome:
        if not self._provider.supports_tools:
            raise AgentReplyError("Agent 回复引擎要求 Provider 支持 function calling")
        context = self._context(request, state)
        strategy = strategy_directive(state)
        if request.webSearch:
            strategy += (
                "\n用户已开启联网搜索：需要最新政策动态、申报窗口、时效性信息或本地库没有的事实时，"
                "调用 search_web 检索全网公开信息；引用网络结果必须附来源标题与 URL，"
                "不得由摘要编造事实、金额或日期；本地政策库与资格工具仍是资格结论的唯一来源。"
                "构造检索词必须包含当前年月（如「苏州 毕业生 创业补贴 2026年 最新」），否则搜索会命中往年旧文；"
                "用户询问「最近/最新/今年」类信息时必须传 time_range 参数（week/month/year）；"
                "对结果中发布日期较旧的内容要注明其发布时间，不得当作最新政策呈现。"
            )
        messages: list[AgentMessage] = [
            {
                "role": "system",
                "content": (
                    f"{AGENT_REPLY_SYSTEM_PROMPT}\n\n"
                    f"{current_date_directive()}\n\n"
                    f"本轮回复策略：\n{strategy}\n\n"
                    "结构化 Agent State（唯一事实来源）：\n"
                    f"{json.dumps(state.model_dump(mode='json'), ensure_ascii=False, separators=(',', ':'))}"
                ),
            },
            *history,
            {"role": "user", "content": request.message.strip()},
        ]
        rounds = 0
        tool_calls_total = 0
        tools = self._registry.definitions(web_search=request.webSearch)
        while rounds < self._max_tool_rounds:
            rounds += 1
            response = await self._provider.complete_with_tools(messages, tools)
            if response.content and not response.tool_calls:
                return self._finalize(response.content, state, context, rounds, tool_calls_total, used_tools=rounds > 1)
            if response.tool_calls:
                tool_calls_total += len(response.tool_calls)
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": call.arguments},
                        }
                        for call in response.tool_calls
                    ],
                })
                for call in response.tool_calls:
                    result = await self._registry.execute(call.name, call.arguments, context)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    })
                continue
            raise AgentReplyError("模型既未返回文本也未返回工具调用")
        raise AgentReplyError(f"Agent 工具循环超过 {self._max_tool_rounds} 轮上限")

    # ----------------------------------------------------------------- guard

    def _finalize(
        self,
        reply: str,
        state: GovernmentAgentState,
        context: ReplyToolContext,
        rounds: int,
        tool_calls: int,
        *,
        used_tools: bool,
    ) -> AgentReplyOutcome:
        reply = reply.strip()
        if not reply:
            raise AgentReplyError("模型返回了空回复")
        if not self._grounded(reply, state, context):
            raise AgentReplyError("回复未通过事实接地校验")
        return AgentReplyOutcome(
            reply=reply,
            tool_rounds=rounds,
            tool_calls=tool_calls,
            grounded=True,
            used_tools=used_tools,
            sources=list(context.web_search_results),
        )

    def _grounded(self, reply: str, state: GovernmentAgentState, context: ReplyToolContext) -> bool:
        # 旧硬规则：历史/关闭参考存在时必须走确定性回复。
        if state.policyReferenceNotices:
            return False
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            return False
        allowed_names = set(context.allowed_policy_names)
        for policy in state.candidatePolicies:
            allowed_names.add(policy.name)
        for evidence in state.knowledgeEvidences:
            allowed_names.add(evidence.policyName)
        for hit in state.realtimePolicyHits:
            if hit.title:
                allowed_names.add(hit.title)
        # 引用的政策名/材料名/文件名必须来自 State、工具结果或实时证据；
        # State 原文（如 requiredMaterials 中的《...申请表》）与工具返回原文同样视为已接地。
        state_text = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
        for name in _POLICY_NAME_PATTERN.findall(reply):
            if (
                name not in allowed_names
                and name not in state_text
                and not any(name in text for text in context.tool_result_texts)
            ):
                logger.info("agent_reply_grounding_reject reason=unknown_policy_name name=%s", name)
                return False
        amount_match = _INVENTED_AMOUNT_PATTERN.search(reply)
        if amount_match and not (
            amount_match.group(0) in state_text
            or any(amount_match.group(0) in text for text in context.tool_result_texts)
        ):
            logger.info("agent_reply_grounding_reject reason=ungrounded_amount")
            return False
        # 旧硬规则：画像不足的追问场景，禁止无来源的具体政策推荐或编造补贴金额。
        # 联网搜索结果自带来源与金额，属于有据引用，不做该限制。
        if (
            not state.candidatePolicies
            and not context.allowed_policy_ids
            and not context.web_search_results
        ):
            if _RECOMMENDATION_PATTERN.search(reply) or _INVENTED_AMOUNT_PATTERN.search(reply):
                logger.info("agent_reply_grounding_reject reason=ungrounded_recommendation")
                return False
        return True

    @staticmethod
    def _context(request: ChatRequest, state: GovernmentAgentState) -> ReplyToolContext:
        return ReplyToolContext(
            profile=state.userProfile,
            material_declarations=dict(state.materialDeclarations),
        )
