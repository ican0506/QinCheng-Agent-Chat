"""内部 Agent State 到用户可读回复的确定性映射。"""
from __future__ import annotations

from app.agent.models import GovernmentAgentState
from app.realtime_policy.models import RealtimeSearchStatus
from app.services.policy_query_context import ConversationIntent, PolicyDomainIntent, UserGoal


class PresentationAdapter:
    """只读取强类型 state，不暴露检索实现或内部调度术语。"""

    @classmethod
    def fallback_reply(cls, state: GovernmentAgentState) -> str:
        local = cls._local_reply(state)
        realtime = cls._realtime_reply(state)
        return local + ("\n\n" + realtime if realtime else "")

    @classmethod
    def _realtime_reply(cls, state: GovernmentAgentState) -> str:
        status = state.realtimeSearchStatus
        if status is RealtimeSearchStatus.NOT_TRIGGERED:
            return ""
        if status is RealtimeSearchStatus.DISABLED:
            return "实时官方信息暂时不可用，本次结果基于已核验政策资料。"
        if status in {RealtimeSearchStatus.TIMEOUT, RealtimeSearchStatus.ERROR}:
            return "实时官方信息暂时无法检索，以下内容仅供参考。"
        if status is RealtimeSearchStatus.NO_RESULTS:
            return "已完成官方信息查询，当前未发现新的相关公开通知。"
        hits = cls._relevant_realtime_hits(state)
        if not hits:
            return ""
        lines = ["相关官方公开信息："]
        for hit in hits:
            lines.extend([hit.title, "官方来源：" + hit.url])
            if hit.publishedAt:
                lines.append("发布时间：" + hit.publishedAt.isoformat())
            if hit.relatedPolicyId is None:
                lines.append("该通知尚未完成结构化核验，不能据此自动判断个人资格。")
        return "\n".join(lines)

    @staticmethod
    def _relevant_realtime_hits(state: GovernmentAgentState):
        """将已检索结果与本轮主题再次对齐；不修改原始检索审计结果。"""
        topics = (
            "就业", "创业", "毕业", "见习", "社保", "社会保险", "补贴", "求职", "申报", "申请", "灵活就业",
        )
        requested = {topic for topic in topics if topic in state.userMessage}
        if not requested:
            return []
        return [
            hit for hit in state.realtimePolicyHits
            if hit.relatedPolicyId is not None or any(topic in f"{hit.title} {hit.snippet}" for topic in requested)
        ]

    @classmethod
    def _local_reply(cls, state: GovernmentAgentState) -> str:
        if state.userGoal is UserGoal.CONVERSATIONAL:
            return cls._conversational_reply(state)
        if state.domainIntent is PolicyDomainIntent.OUT_OF_SCOPE:
            return "当前助手主要支持高校毕业生就业创业政策咨询，暂不提供该主题的解答。"
        if state.candidatePolicies and all(
            policy.policyId in state.policyReferenceNotices for policy in state.candidatePolicies
        ):
            if len(state.candidatePolicies) == 1:
                return state.policyReferenceNotices[state.candidatePolicies[0].policyId]
            return "\n\n".join(
                f"《{policy.name}》：{state.policyReferenceNotices[policy.policyId]}"
                for policy in state.candidatePolicies
            )
        if state.userGoal is UserGoal.POLICY_FACT:
            if not state.candidatePolicies and not state.knowledgeEvidences:
                return "暂未找到与该问题高度相关的政策资料。"
            lines = ["已找到以下政策资料："]
            for policy in state.candidatePolicies:
                lines.append(f"《{policy.name}》")
                if policy.conditions:
                    lines.append("申请条件：" + "；".join(policy.conditions))
                if policy.requiredMaterials:
                    lines.append("申请材料：" + "；".join(policy.requiredMaterials))
                lines.append("官方来源：" + policy.sourceUrl)
                notice = state.policyReferenceNotices.get(policy.policyId)
                if notice:
                    lines.append("时效提示：" + notice)
            for evidence in state.knowledgeEvidences:
                lines.extend([
                    f"《{evidence.policyName}》",
                    evidence.chunkText,
                    "官方来源：" + evidence.sourceUrl,
                    "时效提示：" + cls._knowledge_notice(evidence.currentness),
                ])
            lines.append("以上为政策事实说明，不代表对您个人资格的判断。")
            return "\n".join(lines)
        if state.userGoal is UserGoal.JOB_SEARCH:
            names = "、".join(policy.name for policy in state.candidatePolicies[:2])
            return f"如果你的目标是尽快找工作，当前可优先关注{names or '就业服务和高校毕业生就业支持'}。"
        if state.userGoal is UserGoal.POLICY_DISCOVERY:
            names = "、".join(policy.name for policy in state.candidatePolicies[:3])
            return f"根据你目前提供的信息，可先了解：{names or '高校毕业生就业创业支持'}。"
        if state.userGoal is UserGoal.APPLICATION_GUIDE and state.candidatePolicies:
            policy = state.candidatePolicies[0]
            parts = [f"《{policy.name}》可按以下流程了解和办理："]
            if policy.process:
                parts.append("办理流程：" + "；".join(policy.process))
            if policy.requiredMaterials:
                parts.append("参考材料：" + "；".join(policy.requiredMaterials))
            parts.extend(["官方来源：" + policy.sourceUrl, "具体受理要求请以官方办事指南为准。"])
            return "\n".join(parts)
        if state.needFollowUp and state.followUpQuestions:
            return "要判断你是否符合当前政策，还需要确认：" + "；".join(state.followUpQuestions)
        if not state.candidatePolicies:
            return "暂未找到与当前信息高度相关的政策，可以补充地区、毕业时间或就业创业情况后继续查询。"
        return "已完成政策匹配和初步资格辅助判断，请查看右侧工作台了解具体结果。"

    @staticmethod
    def _conversational_reply(state: GovernmentAgentState) -> str:
        intent = state.conversationIntent
        if intent is ConversationIntent.GREETING:
            return "你好！我是青程 Agent，可以帮你了解高校毕业生就业创业政策、办理流程或资格判断。"
        if intent is ConversationIntent.GRATITUDE:
            return "不客气。需要了解政策、办理流程或资格判断时，随时告诉我。"
        if intent is ConversationIntent.IDENTITY:
            return "我是青程 Agent，主要协助高校毕业生了解就业创业政策、办理流程和资格判断。"
        if intent is ConversationIntent.PAUSE:
            return "好的，我先不查询政策。之后你想继续时，直接告诉我需要了解什么即可。"
        if intent is ConversationIntent.CORRECTION:
            known = []
            labels = {
                "city": "所在地区", "residencyRegistration": "户籍", "education": "学历",
                "graduationYear": "毕业年份", "graduationMonth": "毕业月份", "employmentStatus": "就业状态",
            }
            for field, label in labels.items():
                value = getattr(state.userProfile, field, None)
                if value not in {None, ""}:
                    known.append(f"{label}：{value}")
            if not known:
                return "你说得对。在你没有明确提供个人情况时，我不应该作个性化推断；目前我没有你的个人画像。"
            return "我只会使用当前对话中你明确提供的信息：" + "；".join(known) + "。如果此前表达造成误解，抱歉；我不会自行补全你的个人情况。"
        return "我在。你可以直接说想了解的就业创业政策、办理流程，或需要完成的事。"

    @staticmethod
    def _knowledge_notice(currentness: str) -> str:
        if currentness == "HISTORICAL":
            return "该资料属于历史政策或历史通知，不能据此认为当前仍开放。"
        if currentness == "UNKNOWN":
            return "当前有效性尚未完成结构化确认，办理前应以最新官方通知为准。"
        return "该资料标记为当前政策资料，仍需以官方办理要求为准。"
