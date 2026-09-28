from __future__ import annotations

from datetime import date
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
    graduationDate: date | None = Field(default=None, exclude=True)
    employmentStatus: Literal["待就业", "已就业", "创业中"] | None = None
    isFirstTimeEntrepreneur: bool | None = None
    enterpriseRegisterDate: str | None = None
    businessRegistrationMonths: int | None = Field(default=None, exclude=True)
    socialInsuranceMonths: int | None = None
    residencyRegistration: str | None = Field(default=None, exclude=True)
    unemploymentStatus: str | None = Field(default=None, exclude=True)
    flexibleEmploymentInsurance: bool | None = Field(default=None, exclude=True)
    jobSeekingIntent: bool | None = Field(default=None, exclude=True)
    hardshipIdentity: str | None = Field(default=None, exclude=True)
    housingStatus: Literal["租房", "自有", "其他"] | None = None
    fields: list[ProfileField] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessionId: str = Field(min_length=8, max_length=128)
    userId: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=20_000)
    userProfile: UserProfile = Field(default_factory=UserProfile)


class ChatData(BaseModel):
    sessionId: str
    replyText: str
    needFollowUp: bool = False
    followUpQuestions: list[str] = Field(default_factory=list)
    userProfile: UserProfile
    policies: list[dict[str, Any]] = Field(default_factory=list)
    eligibility: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    materialResults: list[dict[str, Any]] = Field(default_factory=list)


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    traceId: str
    data: T | None
