"""确定性咨询领域与查询目标；不读取历史全文，不决定政策资格。"""
from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel

from app.services.profile_update_parser import ProfileUpdateParser


class PolicyDomainIntent(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCERTAIN = "UNCERTAIN"


class PolicyQueryMode(str, Enum):
    FACT_QUERY = "FACT_QUERY"
    PERSONALIZED_QUERY = "PERSONALIZED_QUERY"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCERTAIN = "UNCERTAIN"


class UserGoal(str, Enum):
    """当前轮对话要完成的用户任务；仅用于后端调度。"""

    POLICY_FACT = "POLICY_FACT"
    POLICY_DISCOVERY = "POLICY_DISCOVERY"
    JOB_SEARCH = "JOB_SEARCH"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    APPLICATION_GUIDE = "APPLICATION_GUIDE"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    FOLLOW_UP_REPLY = "FOLLOW_UP_REPLY"
    CONVERSATIONAL = "CONVERSATIONAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class RouteDecision(BaseModel):
    """当前轮允许使用的能力；由 GoalResolver 的结果唯一决定。"""

    needsProfileGate: bool = False
    runPolicySearch: bool = False
    runEligibility: bool = False
    runMaterialCheck: bool = False
    runPlan: bool = False
    allowKnowledgeEvidence: bool = False
    generateSuggestions: bool = False


class GoalResolver:
    """集中解析用户当前目标，明确表达优先于会话中的上一目标。"""

    @staticmethod
    def resolve(message: str, previous: UserGoal | None = None) -> UserGoal:
        if ConversationIntentDetector.detect(message) is not None:
            return UserGoal.CONVERSATIONAL
        if PolicyDomainIntentDetector.detect(message) is PolicyDomainIntent.OUT_OF_SCOPE:
            return UserGoal.OUT_OF_SCOPE
        # 明确的新目标始终先于“沿用上一轮”。
        if re.search(r"先不(?:管|考虑).*(?:补贴|资格)|只想(?:找工作|就业)|不想(?:创业|申请补贴)|先不用判断资格", message):
            return UserGoal.JOB_SEARCH
        # 材料准备情况是正在办理/资格判断任务的会话内回复；材料名称常含“申请”，
        # 必须在办理指南路由前识别，避免丢失当前资格任务及其材料状态。
        if previous is UserGoal.ELIGIBILITY_CHECK and re.search(
            r"已经准备好|准备好了|准备好|已准备|还没有|没准备|未准备|我有|已有", message
        ):
            return UserGoal.FOLLOW_UP_REPLY
        # 有明确上下文的短追问不是普通“沿用上一轮”。先识别其实际业务动作，
        # 由 Graph 使用 activePolicy 锁定同一条结构化政策。
        if previous is not None and re.fullmatch(r"\s*(?:那)?(?:我)?(?:可以吗|符合吗|能(?:申请|申领)?吗)\s*[？?。！!]*\s*", message):
            return UserGoal.ELIGIBILITY_CHECK
        if previous is not None and re.fullmatch(r"\s*(?:那)?(?:需要|要)?(?:准备)?什么材料|(?:那)?去哪里申请|(?:那)?怎么办理\s*[？?。！!]*\s*", message):
            return UserGoal.APPLICATION_GUIDE
        if re.search(r"怎么(?:办理|申请|申领)|如何(?:办理|申请|申领)|办理流程|申请流程|去哪里申请|什么材料|准备什么材料", message):
            return UserGoal.APPLICATION_GUIDE
        query_mode = PolicyQueryModeDetector.detect(message)
        if query_mode is PolicyQueryMode.PERSONALIZED_QUERY:
            return UserGoal.ELIGIBILITY_CHECK
        if query_mode is PolicyQueryMode.FACT_QUERY:
            return UserGoal.POLICY_FACT
        if re.search(r"(?:继续|我要|我想)?申请.*(?:补贴|政策)", message):
            return UserGoal.ELIGIBILITY_CHECK
        if re.search(r"我(?:是否|能否|能不能|符合)|可以吗|帮我判断.*(?:资格|符合)|我.*符合.*(?:补贴|政策)", message):
            return UserGoal.ELIGIBILITY_CHECK
        if re.search(r"灵活就业|自己.*(?:交|缴).*(?:社保|社会保险)|(?:社保|社会保险).*补贴", message):
            return UserGoal.POLICY_DISCOVERY
        if re.search(r"只想(?:找工作|就业)|找工作|找单位就业|就业服务|求职", message) and not re.search(r"补贴.*(?:条件|资格|申请)", message):
            return UserGoal.JOB_SEARCH
        if ProfileOnlyUpdateDetector.detect(message):
            if previous is not None:
                return UserGoal.FOLLOW_UP_REPLY
            return UserGoal.PROFILE_UPDATE
        if re.search(r"有什么(?:就业|创业)?(?:支持|政策|补贴)|哪些(?:就业|创业)?(?:支持|政策|补贴)|就业支持", message):
            return UserGoal.POLICY_DISCOVERY
        if re.search(r"那下一步|下一步.*(?:干什么|怎么做)|接下来", message) and previous is not None:
            return UserGoal.FOLLOW_UP_REPLY
        if ContextualFollowUpDetector.detect(message) and previous is not None:
            return UserGoal.FOLLOW_UP_REPLY
        # 明确就业创业政策域信号仍维持既有政策发现语义；只有完全没有业务
        # 信号的普通表达才进入 CONVERSATIONAL。
        if PolicyDomainIntentDetector.detect(message) is PolicyDomainIntent.IN_SCOPE:
            return UserGoal.POLICY_DISCOVERY
        return UserGoal.CONVERSATIONAL


class RouteDecider:
    """将目标转换为能力许可，不在节点中重复判断自然语言。"""

    @staticmethod
    def decide(goal: UserGoal, previous_goal: UserGoal | None = None) -> RouteDecision:
        effective_goal = previous_goal if goal is UserGoal.FOLLOW_UP_REPLY and previous_goal else goal
        if effective_goal is UserGoal.ELIGIBILITY_CHECK:
            return RouteDecision(
                needsProfileGate=True,
                runPolicySearch=True,
                runEligibility=True,
                runMaterialCheck=True,
                runPlan=True,
                generateSuggestions=True,
            )
        if effective_goal is UserGoal.POLICY_FACT:
            return RouteDecision(
                runPolicySearch=True,
                allowKnowledgeEvidence=True,
                generateSuggestions=True,
            )
        if effective_goal is UserGoal.APPLICATION_GUIDE:
            return RouteDecision(
                runPolicySearch=True,
                runMaterialCheck=True,
                runPlan=True,
                generateSuggestions=True,
            )
        if effective_goal in {UserGoal.POLICY_DISCOVERY, UserGoal.JOB_SEARCH}:
            return RouteDecision(runPolicySearch=True, generateSuggestions=True)
        return RouteDecision()


class ConversationIntent(str, Enum):
    GREETING = "GREETING"
    GRATITUDE = "GRATITUDE"
    IDENTITY = "IDENTITY"
    CORRECTION = "CORRECTION"
    PAUSE = "PAUSE"


class ConversationIntentDetector:
    """集中识别不应触发业务工具的会话元表达。"""

    @staticmethod
    def detect(message: str) -> ConversationIntent | None:
        text = message.strip()
        if re.fullmatch(r"(?:你)?好[呀啊！!。]?|嗨[！!。]?|哈喽[！!。]?", text):
            return ConversationIntent.GREETING
        if re.fullmatch(r"(?:谢谢|感谢|多谢|辛苦了)[！!。]?", text):
            return ConversationIntent.GRATITUDE
        if re.search(r"你(?:是|是谁|能做什么)|介绍一下你自己", text):
            return ConversationIntent.IDENTITY
        if re.search(r"我(?:都)?没(?:有)?(?:给你)?说|你怎么知道|你理解错了|不是这个意思|别(?:乱|自行)?推断", text):
            return ConversationIntent.CORRECTION
        if re.search(r"先别(?:查|搜|管).*(?:政策|补贴|资格)|先不用(?:查|搜|判断)", text):
            return ConversationIntent.PAUSE
        return None


class ContextualFollowUpDetector:
    """短追问必须依赖 active goal，不能只根据当前短文本猜测新任务。"""

    @staticmethod
    def detect(message: str) -> bool:
        return bool(re.fullmatch(
            r"\s*(?:那)?(?:这个呢|我可以吗|还能(?:申请|申领)吗|继续(?:申请|办理)?|"
            r"还有什么适合我的|需要什么条件|怎么办理)\s*[？?。！!]*\s*",
            message,
        ))


class UserGoalDetector:
    """旧调用点兼容层；新的业务代码应使用 GoalResolver。"""

    @staticmethod
    def detect(message: str, previous: UserGoal | None = None) -> UserGoal:
        return GoalResolver.resolve(message, previous)


class PolicyQueryModeDetector:
    @staticmethod
    def detect(message: str) -> PolicyQueryMode:
        if PolicyDomainIntentDetector.detect(message) is PolicyDomainIntent.OUT_OF_SCOPE:
            return PolicyQueryMode.OUT_OF_SCOPE

        # “我是否符合/能申请什么”依赖个人画像，不能按政策事实问答处理。
        if re.search(
            r"根据我的情况|我(?:现在)?能申请什么|我符合|我能否|我能不能|我可以(?:申请|申领)|"
            r"我.*(?:符合|能否|能不能|可以).*(?:申请|申领|领取|拿到)|"
            r"我想申请|我要申请|帮我申请",
            message,
        ):
            return PolicyQueryMode.PERSONALIZED_QUERY

        # 明确询问政策本身的条件、材料、流程、窗口或官方通知，不要求先补齐画像。
        specific_policy = bool(re.search(
            r"一次性创业补贴|创业(?:社会保险|社保)补贴|灵活就业(?:社会保险|社保)补贴|"
            r"求职创业补贴|就业见习|灵活就业.*(?:社会保险|社保)",
            message,
        ))
        fact_signal = bool(re.search(
            r"条件|材料|流程|办理|申报时间|截止|什么时候|现在还能申请|现在还能申领|窗口开了吗|"
            r"多少钱|补贴标准|标准|是什么|含义|"
            r"有什么补贴|有哪些补贴|适合哪些(?:毕业生|人群)?",
            message,
        ))
        if (
            (specific_policy and fact_signal)
            or re.search(r"这个政策.*(?:条件|材料|流程|截止)", message)
            or re.search(r"历史(?:政策|通知|申报)|往年.*(?:通知|申报)", message)
            or (specific_policy and re.search(r"只看|想看|查询", message))
        ):
            return PolicyQueryMode.FACT_QUERY

        if ProfileOnlyUpdateDetector.detect(message):
            return PolicyQueryMode.PROFILE_UPDATE
        if PolicyDomainIntentDetector.detect(message) is PolicyDomainIntent.IN_SCOPE:
            return PolicyQueryMode.UNCERTAIN
        return PolicyQueryMode.UNCERTAIN


class QueryTemporalIntent(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"


class QueryTemporalIntentDetector:
    @staticmethod
    def detect(message: str) -> QueryTemporalIntent:
        # 毕业年份/届别不是历史检索意图，必须有历史政策或通知语义。
        if re.search(r"历史政策|历史通知|历史申报|往年.*(?:申报|政策|通知)|(?:之前|过去|去年)的(?:申报)?通知|当时.*(?:申请|申报|截止|通知)", message):
            return QueryTemporalIntent.HISTORICAL
        return QueryTemporalIntent.CURRENT


class ProfileOnlyUpdateDetector:
    @staticmethod
    def detect(message: str) -> bool:
        if re.search(r"补贴|政策|通知|申报|申请|条件|材料|办理|截止|有什么|有哪些|找工作|创业打算|准备创业|打算创业", message):
            return False
        return bool(ProfileUpdateParser.parse(message) or re.search(r"毕业|就业了|毕业日期", message))


class PolicyDomainIntentDetector:
    @staticmethod
    def detect(message: str) -> PolicyDomainIntent:
        if re.search(r"政策|就业|创业|毕业|见习|申报|申请|补贴|社保|社会保险|找工作|材料", message):
            return PolicyDomainIntent.IN_SCOPE if len(message.strip()) > 3 else PolicyDomainIntent.UNCERTAIN
        if re.search(r"电影|吃什么|笑话|天气|游戏|旅游", message):
            return PolicyDomainIntent.OUT_OF_SCOPE
        # 画像补充和暂不明确的表达不被误杀；只有明确无关主题才拒绝。
        return PolicyDomainIntent.UNCERTAIN


class PolicyQueryContextResolver:
    @staticmethod
    def resolve(message: str, previous: str | None) -> tuple[str | None, str]:
        if ConversationIntentDetector.detect(message) is not None:
            # 闲聊与质疑不能把上一轮检索词重新送进本轮工具调用；旧任务本身
            # 由 active goal 保留，等待用户明确补充或继续。
            return previous, message
        reset = bool(re.search(r"换个问题|重新开始", message))
        if reset:
            previous = None
            message = re.sub(r"换个问题|重新开始", "", message).strip(" ，,。")
        if PolicyDomainIntentDetector.detect(message) is PolicyDomainIntent.OUT_OF_SCOPE:
            return None, message
        if not message:
            return None, ""
        if previous and ProfileOnlyUpdateDetector.detect(message):
            return previous, previous
        # 后面的明确目标优先，例如“不看就业了，想了解创业补贴”。
        clauses = re.split(r"[，,。；;]", message)
        goal = None
        for clause in reversed(clauses):
            if re.search(r"不看|不想了解", clause):
                continue
            if "求职创业补贴" in clause:
                goal = "求职创业补贴"
            elif "创业社会保险补贴" in clause or "创业社保补贴" in clause:
                goal = "创业社会保险补贴"
            elif "一次性创业补贴" in clause:
                goal = "一次性创业补贴"
            elif "灵活就业" in clause or re.search(r"自己.*(?:社保|社会保险)", clause):
                goal = "灵活就业社会保险补贴"
            elif "见习" in clause:
                goal = "就业见习"
            elif "创业" in clause and ProfileUpdateParser.deterministic_intent_overrides(clause).get('entrepreneurshipIntent') is not False:
                goal = "创业补贴"
            elif re.search(r"就业|求职|找工作", clause):
                goal = "就业补贴"
            elif re.search(r"社保|社会保险", clause) and not ProfileOnlyUpdateDetector.detect(clause):
                goal = "社会保险补贴"
            elif "补贴" in clause:
                goal = "就业创业补贴"
            if goal:
                break
        if goal:
            if QueryTemporalIntentDetector.detect(message) is QueryTemporalIntent.HISTORICAL:
                cohort = re.search(r"20\d{2}(?:届|年)", message)
                goal = f"{cohort.group() if cohort else ''}历史通知 {goal}"
            return goal, message
        if previous:
            return previous, previous
        # 首次完整画像视作隐含就业创业咨询，但不储存个人原文。
        patch = ProfileUpdateParser.parse(message)
        if ProfileOnlyUpdateDetector.detect(message) and (patch.get('employmentStatus') or len(patch) >= 3):
            goal = "创业补贴" if patch.get('employmentStatus') == '创业中' else "就业补贴"
            return goal, goal
        return None, message
