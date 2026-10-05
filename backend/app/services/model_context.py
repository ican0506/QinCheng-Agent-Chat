"""统一构造模型输入；只将后端已经确定的事实暴露给模型。"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field

from app.agent.models import GovernmentAgentState
from app.services.llm.base import AgentMessage, LLMMessage
from app.services.policy_query_context import UserGoal


QINGCHENG_SYSTEM_PROMPT = """你是青程 Agent，服务高校毕业生就业创业场景。
优先解决用户当前目标，先回答，再仅在完成当前目标确实需要时追问；不要为了补全画像机械追问。
下方“已核验上下文”由后端确定，是政策事实、用户画像、资格与办理状态的唯一依据。
资格判断结果只能解释，不能重新计算、覆盖或推导为其他结论；官方资料也不能直接推导个人是否符合，更不能说用户符合。
不得编造金额、日期、材料、资格条件、办理状态或政策名称；证据不足时明确说明暂无法确认。
优先给出官方来源。不得向用户暴露任何内部技术、检索、编排或状态枚举名称。"""


class ResponseMode(str, Enum):
    DIRECT_ANSWER = "DIRECT_ANSWER"
    RECOMMENDATION = "RECOMMENDATION"
    ELIGIBILITY_EXPLANATION = "ELIGIBILITY_EXPLANATION"
    APPLICATION_GUIDE = "APPLICATION_GUIDE"
    FOLLOW_UP = "FOLLOW_UP"


class ModelContext(BaseModel):
    """仅用于生成模型输入，不写入 Session，也不替代 GovernmentAgentState。"""

    currentUserMessage: str
    conversationHistory: list[AgentMessage] = Field(default_factory=list)
    userProfile: dict[str, str] = Field(default_factory=dict)
    userGoal: str
    activeGoal: str | None = None
    activePolicy: str | None = None
    responseMode: ResponseMode
    policyCandidates: list[dict[str, object]] = Field(default_factory=list)
    officialEvidence: list[dict[str, str]] = Field(default_factory=list)
    eligibilityResult: list[dict[str, object]] = Field(default_factory=list)
    materialResults: list[dict[str, object]] = Field(default_factory=list)
    plan: dict[str, object] | None = None
    missingRequiredFields: list[str] = Field(default_factory=list)
    suggestedActions: list[str] = Field(default_factory=list)

    def to_prompt_text(self) -> str:
        """字段已中文化、裁剪且无 Provider/score/raw metadata。"""
        return json.dumps(self._prompt_data(), ensure_ascii=False, separators=(",", ":"))

    def _prompt_data(self) -> dict[str, object]:
        return {
            "当前用户问题": self.currentUserMessage,
            "已确认画像": self.userProfile,
            "当前目标": self.userGoal,
            "当前政策": self.activePolicy,
            "回复方式": self._response_mode_label(),
            "候选政策": self.policyCandidates,
            "官方依据": self.officialEvidence,
            "资格判断": self.eligibilityResult,
            "材料状态": self.materialResults,
            "办理步骤": self.plan,
            "需要补充的信息": self.missingRequiredFields,
            "可选下一步": self.suggestedActions,
        }

    def _response_mode_label(self) -> str:
        return {
            ResponseMode.DIRECT_ANSWER: "直接回答政策事实",
            ResponseMode.RECOMMENDATION: "推荐相关支持方向",
            ResponseMode.ELIGIBILITY_EXPLANATION: "解释后端已完成的资格判断",
            ResponseMode.APPLICATION_GUIDE: "说明材料、流程和官方来源",
            ResponseMode.FOLLOW_UP: "只追问当前目标真正缺少的信息",
        }[self.responseMode]


class ModelContextBuilder:
    """唯一的 State → LLM context 选择器。"""

    _PROFILE_LABELS = {
        "city": "地区", "residencyRegistration": "户籍", "education": "学历",
        "graduationYear": "毕业年份", "graduationMonth": "毕业月份",
        "employmentStatus": "就业状态", "flexibleEmploymentInsurance": "灵活就业参保情况",
        "entrepreneurshipIntent": "创业意向",
    }
    _STATUS_LABELS = {
        "PASS": "当前规则判断符合", "FAIL": "当前规则判断不符合",
        "UNKNOWN": "信息不足", "MANUAL_REVIEW": "需要人工或官方核验",
    }

    def __init__(self, *, history_limit: int = 6, evidence_limit: int = 3, excerpt_limit: int = 500) -> None:
        self._history_limit = history_limit
        self._evidence_limit = evidence_limit
        self._excerpt_limit = excerpt_limit

    def build(self, state: GovernmentAgentState, history: list[AgentMessage]) -> ModelContext:
        mode = self._response_mode(state)
        include_eligibility = mode is ResponseMode.ELIGIBILITY_EXPLANATION
        include_application = mode is ResponseMode.APPLICATION_GUIDE
        return ModelContext(
            currentUserMessage=state.userMessage.strip(),
            conversationHistory=self._history(history),
            userProfile=self._profile(state),
            userGoal=self._goal_label(state.userGoal),
            activeGoal=self._goal_label(state.activeGoal) if state.activeGoal else None,
            activePolicy=next((policy.name for policy in state.candidatePolicies if policy.policyId == state.activePolicy), None),
            responseMode=mode,
            policyCandidates=self._policies(state, include_application=include_application),
            officialEvidence=self._evidence(state),
            eligibilityResult=self._eligibility(state) if include_eligibility else [],
            materialResults=self._materials(state) if include_application or include_eligibility else [],
            plan=self._plan(state) if include_application or include_eligibility else None,
            missingRequiredFields=list(state.followUpQuestions),
            suggestedActions=[action.label for action in state.suggestedActions],
        )

    def final_messages(self, state: GovernmentAgentState, history: list[AgentMessage]) -> tuple[ModelContext, list[LLMMessage]]:
        context = self.build(state, history)
        messages: list[LLMMessage] = [
            {"role": "system", "content": self._system_message(context)},
            *[message for message in context.conversationHistory if message.get("role") in {"user", "assistant"}],
            {"role": "user", "content": context.currentUserMessage},
        ]
        return context, messages

    def agent_system_message(self, context: ModelContext, *, web_search: bool) -> str:
        addition = ""
        if web_search:
            addition = "\n用户已开启联网查询：仅引用返回的公开来源，不得由摘要补写事实或资格结论。"
        return self._system_message(context) + addition

    def _system_message(self, context: ModelContext) -> str:
        return f"{QINGCHENG_SYSTEM_PROMPT}\n\n{current_date_directive()}\n\n已核验上下文：\n{context.to_prompt_text()}"

    def _history(self, history: list[AgentMessage]) -> list[AgentMessage]:
        return [dict(item) for item in history[-self._history_limit:] if item.get("role") in {"user", "assistant"}]

    def _profile(self, state: GovernmentAgentState) -> dict[str, str]:
        return {
            label: str(value)
            for field, label in self._PROFILE_LABELS.items()
            if (value := getattr(state.userProfile, field, None)) not in {None, ""}
        }

    def _policies(self, state: GovernmentAgentState, *, include_application: bool) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for policy in state.candidatePolicies[:self._evidence_limit]:
            item: dict[str, object] = {
                "政策名称": policy.name, "摘要": policy.summary,
                "申请条件": policy.conditions, "官方来源": policy.sourceUrl,
            }
            if include_application:
                item.update({"参考材料": policy.requiredMaterials, "办理流程": policy.process})
            result.append(item)
        return result

    def _evidence(self, state: GovernmentAgentState) -> list[dict[str, str]]:
        evidence: list[dict[str, str]] = []
        for hit in state.realtimePolicyHits[:self._evidence_limit]:
            item = {
                "政策名称": hit.title, "来源标题": hit.title,
                "来源机构": hit.department or hit.domain,
                "官方来源": hit.url, "相关摘录": hit.snippet[:self._excerpt_limit],
            }
            if hit.publishedAt:
                item["发布时间"] = hit.publishedAt.isoformat()
            evidence.append(item)
        remaining = self._evidence_limit - len(evidence)
        for item in state.knowledgeEvidences[:max(remaining, 0)]:
            evidence.append({
                "政策名称": item.policyName, "来源标题": item.policyName,
                "来源机构": "官方政策资料", "官方来源": item.sourceUrl,
                "当前时效": self._currentness(item.currentness),
                "相关摘录": item.chunkText[:self._excerpt_limit],
            })
        return evidence

    def _eligibility(self, state: GovernmentAgentState) -> list[dict[str, object]]:
        return [{
            "政策": next((item.name for item in state.candidatePolicies if item.policyId == result.policyId), result.policyId),
            "判断结果": self._STATUS_LABELS[result.overallStatus.value],
            "说明": result.summary,
            "缺少信息": result.missingFields,
            "条件明细": [condition.model_dump(mode="json") for condition in result.conditionResults],
        } for result in state.eligibilityResults]

    @staticmethod
    def _materials(state: GovernmentAgentState) -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in state.materialResults]

    @staticmethod
    def _plan(state: GovernmentAgentState) -> dict[str, object] | None:
        return state.overallPlan.model_dump(mode="json") if state.overallPlan else None

    @staticmethod
    def _response_mode(state: GovernmentAgentState) -> ResponseMode:
        if state.needFollowUp:
            return ResponseMode.FOLLOW_UP
        if state.userGoal is UserGoal.ELIGIBILITY_CHECK:
            return ResponseMode.ELIGIBILITY_EXPLANATION
        if state.userGoal is UserGoal.APPLICATION_GUIDE:
            return ResponseMode.APPLICATION_GUIDE
        if state.userGoal in {UserGoal.JOB_SEARCH, UserGoal.POLICY_DISCOVERY}:
            return ResponseMode.RECOMMENDATION
        return ResponseMode.DIRECT_ANSWER

    @staticmethod
    def _goal_label(goal: UserGoal | None) -> str:
        return {
            UserGoal.POLICY_FACT: "政策事实咨询", UserGoal.POLICY_DISCOVERY: "政策发现",
            UserGoal.JOB_SEARCH: "就业方向咨询", UserGoal.ELIGIBILITY_CHECK: "资格判断",
            UserGoal.APPLICATION_GUIDE: "办理指引", UserGoal.PROFILE_UPDATE: "更新个人情况",
            UserGoal.FOLLOW_UP_REPLY: "补充当前任务所需信息", UserGoal.OUT_OF_SCOPE: "服务范围说明",
            None: "未明确",
        }[goal]

    @staticmethod
    def _currentness(value: str) -> str:
        return {"HISTORICAL": "历史资料，不能据此认为当前仍开放", "UNKNOWN": "当前有效性尚待确认", "CURRENT": "当前政策资料"}.get(value, "当前有效性尚待确认")


def current_date_directive() -> str:
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        now = datetime.now()
    return f"当前日期：{now.year}年{now.month}月{now.day}日。涉及日期仅可引用已核验上下文，不得自行编造或推测日期。"
