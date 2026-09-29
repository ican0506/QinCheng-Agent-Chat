from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, StrictBool, field_validator

from app.models.chat import UserProfile
from app.services.llm.base import LLMMessage, LLMProvider


PROFILE_EXTRACTION_SYSTEM_PROMPT = """你是用户画像信息抽取器，只从当前用户消息提取明确新增或修改的画像字段。
只允许输出 JSON 对象，且只能使用以下字段：city、education、graduationYear、graduationDate、employmentStatus、socialInsuranceMonths、businessRegistrationMonths、residencyRegistration、unemploymentStatus、flexibleEmploymentInsurance、jobSeekingIntent、hardshipIdentity、entrepreneurshipIntent。
不要输出解释、Markdown、政策、policyId、资格结论、材料、办理计划或任何其他字段。
不要根据社保推断就业状态；不要根据营业执照推断创业资格；不要把“今年毕业”补成日期；用户只说年月毕业时 graduationDate 必须为 null。
未明确的信息省略或设为 null。历史画像只用于理解“之前说错了”等纠正语境；不要重复输出本轮未修改的历史字段。
枚举使用：education 为 本科/硕士/专科/其他；employmentStatus 为 待就业/已就业/创业中。"""


class ProfileExtractionError(ValueError):
    """LLM 的画像结果不符合严格结构化契约。"""


class ProfileExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str | None = None
    education: str | None = None
    graduationYear: int | None = None
    graduationDate: date | None = None
    employmentStatus: str | None = None
    socialInsuranceMonths: int | None = None
    businessRegistrationMonths: int | None = None
    residencyRegistration: str | None = None
    unemploymentStatus: str | None = None
    flexibleEmploymentInsurance: StrictBool | None = None
    jobSeekingIntent: StrictBool | None = None
    hardshipIdentity: str | None = None
    entrepreneurshipIntent: StrictBool | None = None

    @field_validator("graduationYear")
    @classmethod
    def validate_graduation_year(cls, value: int | None) -> int | None:
        if value is not None and (type(value) is not int or not 1900 <= value <= 2100):
            raise ValueError("graduationYear 必须是合理的整数年份")
        return value

    @field_validator("socialInsuranceMonths", "businessRegistrationMonths")
    @classmethod
    def validate_months(cls, value: int | None) -> int | None:
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("月数必须是非负整数")
        return value


class ProfilePatchValidator:
    _education = {"本科", "硕士", "专科", "其他"}
    _employment = {
        "待就业": ("待就业", None, None),
        "未就业": ("待就业", "未就业", None),
        "没工作": ("待就业", "未就业", None),
        "没有工作": ("待就业", "未就业", None),
        "已就业": ("已就业", None, None),
        "有工作": ("已就业", None, None),
        "在职": ("已就业", None, None),
        "创业中": ("创业中", None, True),
        "正在创业": ("创业中", None, True),
    }

    @classmethod
    def validate(cls, content: str, message: str) -> dict[str, object]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProfileExtractionError("invalid_json") from exc
        if not isinstance(payload, dict):
            raise ProfileExtractionError("json_object_required")
        try:
            result = ProfileExtractionResult.model_validate(payload)
        except Exception as exc:
            raise ProfileExtractionError("schema_validation_failed") from exc
        return cls._normalize(result, message)

    @classmethod
    def _normalize(cls, result: ProfileExtractionResult, message: str) -> dict[str, object]:
        patch: dict[str, object] = result.model_dump(exclude_none=True)
        if "city" in patch:
            city = str(patch["city"]).strip()
            if not city:
                raise ProfileExtractionError("invalid_city")
            patch["city"] = "苏州市" if city in {"苏州", "苏州市"} else city
        if "education" in patch:
            education = str(patch["education"]).strip()
            if education not in cls._education:
                raise ProfileExtractionError("invalid_education")
            patch["education"] = education
        if "graduationDate" in patch:
            if not cls._message_has_exact_graduation_date(message):
                raise ProfileExtractionError("graduation_date_precision_missing")
            graduation_date = patch["graduationDate"]
            assert isinstance(graduation_date, date)
            year = patch.get("graduationYear")
            if year is not None and year != graduation_date.year:
                raise ProfileExtractionError("graduation_year_date_conflict")
            patch["graduationYear"] = graduation_date.year
        if "employmentStatus" in patch:
            status = str(patch["employmentStatus"]).strip()
            normalized = cls._employment.get(status)
            if normalized is None:
                raise ProfileExtractionError("invalid_employment_status")
            employment_status, unemployment_status, entrepreneurship_intent = normalized
            patch["employmentStatus"] = employment_status
            if unemployment_status is not None:
                patch["unemploymentStatus"] = unemployment_status
            if entrepreneurship_intent is not None:
                patch["entrepreneurshipIntent"] = entrepreneurship_intent
        if "unemploymentStatus" in patch and patch["unemploymentStatus"] != "未就业":
            raise ProfileExtractionError("invalid_unemployment_status")
        return patch

    @staticmethod
    def _message_has_exact_graduation_date(message: str) -> bool:
        return bool(re.search(r"20\d{2}年\d{1,2}月\d{1,2}日(?:毕业|应届)?", message))


class LLMProfileExtractor:
    """复用现有 Provider 的单次 JSON 调用，抽取当前消息的画像 patch。"""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def extract(self, message: str, current_profile: UserProfile) -> dict[str, object]:
        context = current_profile.model_dump(mode="json", exclude_none=True)
        messages: list[LLMMessage] = [
            {"role": "system", "content": PROFILE_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "currentProfile": context,
                "currentUserMessage": message,
            }, ensure_ascii=False, separators=(",", ":"))},
        ]
        try:
            content = await self._provider.complete(messages)
        except Exception as exc:
            raise ProfileExtractionError("provider_exception") from exc
        return ProfilePatchValidator.validate(content, message)
