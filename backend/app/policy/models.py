from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ConditionOperator(str, Enum):
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    WITHIN_YEARS = "within_years"


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
