from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ProfileField(BaseModel):
    key: str
    value: str
    source: Literal["user_stated", "document_extracted", "system_inferred"]


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    userId: str | None = None
    city: str | None = None
    education: Literal["本科", "硕士", "专科", "其他"] | None = None
    graduationYear: int | None = None
    # 用户只给到年月时不能伪造具体毕业日；月份单独保存供政策规则按年月使用。
    graduationMonth: int | None = Field(default=None, ge=1, le=12)
    graduationDate: date | None = Field(default=None, exclude=True)
    employmentStatus: Literal["待就业", "已就业", "创业中"] | None = None
    isFirstTimeEntrepreneur: bool | None = None
    enterpriseRegisterDate: str | None = None
    businessRegistrationMonths: int | None = Field(default=None, exclude=True)
    socialInsuranceMonths: int | None = None
    residencyRegistration: str | None = None
    unemploymentStatus: str | None = Field(default=None, exclude=True)
    flexibleEmploymentInsurance: bool | None = None
    jobSeekingIntent: bool | None = Field(default=None, exclude=True)
    entrepreneurshipIntent: bool | None = None
    hardshipIdentity: str | None = Field(default=None, exclude=True)
    housingStatus: Literal["租房", "自有", "其他"] | None = None
    fields: list[ProfileField] = Field(default_factory=list)


class MaterialStatus(str, Enum):
    READY = "READY"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class MaterialCheckResult(BaseModel):
    materialId: str
    policyId: str
    materialName: str
    description: str | None = None
    status: MaterialStatus
    reason: str
    source: str = "POLICY"
    userProvided: bool = False
    needsManualReview: bool = False


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessionId: str = Field(min_length=8, max_length=128)
    userId: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=20_000)
    userProfile: UserProfile = Field(default_factory=UserProfile)
    webSearch: bool = False


class SessionProfileUpdateRequest(BaseModel):
    """手动编辑当前会话画像；仅已显式提交的字段参与更新。"""

    model_config = ConfigDict(extra="forbid")

    userId: str = Field(min_length=1, max_length=128)
    profile: UserProfile


class WebSource(BaseModel):
    title: str
    url: str


class SuggestedAction(BaseModel):
    label: str
    prompt: str


class ChatData(BaseModel):
    sessionId: str
    replyText: str
    needFollowUp: bool = False
    followUpQuestions: list[str] = Field(default_factory=list)
    userProfile: UserProfile
    policies: list[dict[str, Any]] = Field(default_factory=list)
    eligibility: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    materialResults: list[MaterialCheckResult] = Field(default_factory=list)
    sources: list[WebSource] = Field(default_factory=list)
    suggestedActions: list[SuggestedAction] = Field(default_factory=list)
    applicationGuide: bool = False


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    traceId: str
    data: T | None
