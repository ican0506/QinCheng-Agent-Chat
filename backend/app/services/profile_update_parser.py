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

        graduation_match = re.search(r"(20\d{2})年(?:\d{1,2}月)?(?:毕业|应届)", message)
        if graduation_match:
            result["graduationYear"] = int(graduation_match.group(1))
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
        if "本市户籍" in message or "苏州户籍" in message:
            result["residencyRegistration"] = "本市户籍"
        self_reported_unemployment = bool(
            re.search(r"(?:我|本人)(?:目前|现在)?(?:还在|正处于|处于)?待业(?:状态)?", message)
            or re.search(r"(?:目前待业|现在(?:还在)?待业|处于待业状态)", message)
        )
        if "未就业" in message or "没找到工作" in message or self_reported_unemployment:
            result["employmentStatus"] = "待就业"
            result["unemploymentStatus"] = "未就业"
        elif "创业中" in message:
            result["employmentStatus"] = "创业中"
        elif "已就业" in message or "在职" in message:
            result["employmentStatus"] = "已就业"

        result.update(ProfileUpdateParser.deterministic_intent_overrides(message))
        if "灵活就业参保" in message or "灵活就业缴社保" in message:
            result["flexibleEmploymentInsurance"] = True
        return result

    @staticmethod
    def deterministic_overrides(message: str, current_date: date | None = None) -> dict[str, object]:
        """仅返回本轮可由规则精确判断的相对毕业年份和明确意图。"""
        return {
            **ProfileUpdateParser.relative_time_overrides(message, current_date),
            **ProfileUpdateParser.deterministic_intent_overrides(message),
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
        if any(phrase in message for phrase in ("我不创业", "不是要创业", "不考虑创业", "暂时不考虑创业", "暂时不创业")):
            result["entrepreneurshipIntent"] = False
        elif any(phrase in message for phrase in ("准备创业", "想自己开公司", "打算创业", "我想创业")):
            result["entrepreneurshipIntent"] = True
        if any(phrase in message for phrase in ("只想找工作", "打算找工作", "准备找单位就业", "只打算找工作", "想找个工作")):
            result["jobSeekingIntent"] = True
        return result
