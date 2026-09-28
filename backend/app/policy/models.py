from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConditionOperator(str, Enum):
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    WITHIN_YEARS = "within_years"


class ValidityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class ApplicationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    NOT_STARTED = "NOT_STARTED"
    UNKNOWN = "UNKNOWN"


class PolicyCondition(BaseModel):
    conditionId: str
    field: str
    operator: ConditionOperator
    value: Any
    description: str
    policyEvidence: str


class PolicyRecord(BaseModel):
    policyId: str
    name: str
    region: str
    department: str
    summary: str
    publishedDate: str | None = None
    effectiveDate: str | None = None
    expiryDate: str | None = None
    sourceUrl: str | None = None
    targetGroups: list[str]
    topics: list[str]
    conditions: list[PolicyCondition]
    requiredMaterials: list[str]
    process: list[str]
    isVerified: bool
    sourceVerified: bool = False
    validityStatus: ValidityStatus = ValidityStatus.UNKNOWN
    lastVerifiedAt: date | None = None
    sourcePublishedDate: date | None = None
    basisDocuments: list[str] = Field(default_factory=list)
    applicationStatus: ApplicationStatus = ApplicationStatus.UNKNOWN
    applicationStartDate: date | None = None
    applicationEndDate: date | None = None
    applicableCohorts: list[str] = Field(default_factory=list)
