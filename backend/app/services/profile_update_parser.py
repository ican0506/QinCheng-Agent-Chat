from __future__ import annotations

import re
from datetime import date


class ProfileUpdateParser:
    """只解析比赛链路所需、表达明确的补充信息。"""

    @staticmethod
    def parse(message: str, current_date: date | None = None) -> dict[str, object]:
        result: dict[str, object] = {}
        if re.search(r"(?:我在|位于|来自)\s*苏州市?", message):
            result["city"] = "苏州市"
        for education in ("本科", "硕士", "专科", "其他"):
            if education in message:
                result["education"] = education
                break

        graduation_match = re.search(r"(20\d{2})年(?:(\d{1,2}|[一二三四五六七八九十]+)月(?:份)?)?(?:毕业|应届)", message)
        if graduation_match:
            result["graduationYear"] = int(graduation_match.group(1))
            if graduation_match.group(2):
                month = ProfileUpdateParser._parse_month(graduation_match.group(2))
                if month is not None:
                    result["graduationMonth"] = month
        else:
            explicit_year_match = re.search(r"毕业年份\s*(?:是|为|[:：])?\s*(20\d{2})", message)
            if explicit_year_match:
                result["graduationYear"] = int(explicit_year_match.group(1))
            else:
                result.update(ProfileUpdateParser.relative_time_overrides(message, current_date))
        result.update(ProfileUpdateParser.graduation_date_overrides(message))
        months = re.search(r"(?:社保|社会保险).{0,8}?(\d{1,3})\s*个?月|(\d{1,3})\s*个?月.{0,4}?(?:社保|社会保险)", message)
        if months:
            result["socialInsuranceMonths"] = int(months.group(1) or months.group(2))
        elif re.search(r"(?:社保|社会保险).{0,8}?(?:一|1)年", message):
            result["socialInsuranceMonths"] = 12
        registration = re.search(r"(?:公司|企业)?.{0,4}?(?:注册|登记).{0,8}?(\d{1,3})\s*个?月", message)
        if registration:
            result["businessRegistrationMonths"] = int(registration.group(1))
        elif re.search(r"(?:公司|企业)?.{0,4}?(?:注册|登记).{0,8}?(?:一|1)年", message):
            result["businessRegistrationMonths"] = 12
        if re.search(r"(?:本市|苏州市?|昆山市?)户籍", message):
            result["residencyRegistration"] = "本市户籍"
        self_reported_unemployment = bool(
            re.search(r"(?:我|本人)(?:目前|现在)?(?:还在|正处于|处于)?待业(?:状态)?", message)
            or re.search(r"(?:目前待业|现在(?:还在)?待业|处于待业状态)", message)
        )
        if (
            "未就业" in message
            or "暂未就业" in message
            or "没找到工作" in message
            or "目前没工作" in message
            or "现在没工作" in message
            or "待就业" in message
            or self_reported_unemployment
        ):
            result["employmentStatus"] = "待就业"
            result["unemploymentStatus"] = "未就业"
        elif "创业中" in message:
            result["employmentStatus"] = "创业中"
        elif "已就业" in message or "在职" in message:
            result["employmentStatus"] = "已就业"

        result.update(ProfileUpdateParser.deterministic_intent_overrides(message))
        result.update(ProfileUpdateParser.flexible_insurance_overrides(message))
        # 否定纠正必须最后覆盖前面由关键词子串得到的正向结果。
        result.update(ProfileUpdateParser.employment_status_overrides(message))
        return result

    @staticmethod
    def _parse_month(value: str) -> int | None:
        if value.isdigit():
            month = int(value)
            return month if 1 <= month <= 12 else None
        numerals = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                    "十一": 11, "十二": 12}
        return numerals.get(value)

    @staticmethod
    def deterministic_overrides(message: str, current_date: date | None = None) -> dict[str, object]:
        """仅返回本轮可由规则精确判断的相对毕业年份和明确意图。"""
        return {
            **ProfileUpdateParser.relative_time_overrides(message, current_date),
            **ProfileUpdateParser.deterministic_intent_overrides(message),
            **ProfileUpdateParser.flexible_insurance_overrides(message),
            **ProfileUpdateParser.employment_status_overrides(message),
        }

    @staticmethod
    def graduation_date_overrides(message: str) -> dict[str, object]:
        """仅在本轮明确提供完整毕业日期时返回精确日期及对应年份。"""
        if not re.search(r"毕业|应届", message):
            return {}
        exact_date_match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", message)
        if exact_date_match is None:
            exact_date_match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", message)
        if exact_date_match is None:
            return {}
        year, month, day = (int(value) for value in exact_date_match.groups())
        try:
            graduation_date = date(year, month, day)
        except ValueError:
            return {}
        return {"graduationYear": year, "graduationDate": graduation_date}

    @staticmethod
    def relative_time_overrides(message: str, current_date: date | None = None) -> dict[str, object]:
        """仅解析相对毕业年份；消息含精确毕业日期时由精确日期负责。"""
        if ProfileUpdateParser.graduation_date_overrides(message):
            return {}
        result: dict[str, object] = {}
        reference_date = current_date or date.today()
        relative_years = {
            "今年": reference_date.year,
            "去年": reference_date.year - 1,
            "前年": reference_date.year - 2,
            "明年": reference_date.year + 1,
        }
        for phrase, year in relative_years.items():
            if re.search(rf"{phrase}(?:\s*(?:本科|硕士|专科|其他))?毕业", message):
                result["graduationYear"] = year
                break
        return result

    @staticmethod
    def deterministic_intent_overrides(message: str) -> dict[str, object]:
        """仅返回本轮明确表达的求职或创业意图。"""
        result: dict[str, object] = {}
        job_only = bool(re.search(r"(?:只(?:是)?(?:打算|想)|就是想|准备)找(?:个)?(?:工作|单位就业)", message))
        negative = bool(re.search(
            r"(?:不(?:是(?:要)?|考虑)?创业)(?!补贴|政策|项目|贷款|相关)|没有创业打算", message
        ))
        if negative or job_only:
            result["entrepreneurshipIntent"] = False
        elif any(phrase in message for phrase in ("准备创业", "想自己开公司", "打算创业", "我想创业")):
            result["entrepreneurshipIntent"] = True
        if job_only or any(phrase in message for phrase in ("打算找工作", "准备找单位就业", "想找个工作")):
            result["jobSeekingIntent"] = True
        return result

    @staticmethod
    def flexible_insurance_overrides(message: str) -> dict[str, object]:
        """只记录参保陈述，不把政策问题当成已参保事实。"""
        for clause in re.split(r"[，,。；;！!？?]", message):
            if re.search(
                r"(?:没有|未|不(?:是|属于)?)(?:按|以)?灵活就业"
                r"(?:身份|人员)?(?:参保|交社保|缴社保)?",
                clause,
            ):
                return {"flexibleEmploymentInsurance": False}
            if re.search(r"什么|是否|怎么|如何|能否|能申请|可以|吗", clause):
                continue
            if re.search(r"灵活就业(?:身份)?(?:参保|交社保|缴社保)", clause):
                return {"flexibleEmploymentInsurance": True}
        return {}

    @staticmethod
    def employment_status_overrides(message: str) -> dict[str, object]:
        """处理明确的就业状态纠正；不把否定短语中的“未就业”当成正向事实。"""
        if re.search(r"已经就业|已就业|已经找到工作|找到工作了|目前在职|现在在职", message):
            return {"employmentStatus": "已就业", "unemploymentStatus": None}
        if re.search(
            r"不是未就业|不是待就业|已经不是待业状态|不再(?:未就业|待就业|待业)",
            message,
        ):
            return {"employmentStatus": None, "unemploymentStatus": None}
        return {}
