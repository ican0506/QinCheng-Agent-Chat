"""确定性咨询领域与查询目标；不读取历史全文，不决定政策资格。"""
from __future__ import annotations

import re
from enum import Enum

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
            r"求职创业补贴|就业见习",
            message,
        ))
        fact_signal = bool(re.search(
            r"条件|材料|流程|办理|申报时间|截止|什么时候|现在还能申请|现在还能申领|窗口开了吗",
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
