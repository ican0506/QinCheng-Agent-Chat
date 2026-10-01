from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RealtimeSearchStatus(str, Enum):
    NOT_TRIGGERED = 'NOT_TRIGGERED'
    DISABLED = 'DISABLED'
    SUCCESS = 'SUCCESS'
    NO_RESULTS = 'NO_RESULTS'
    TIMEOUT = 'TIMEOUT'
    ERROR = 'ERROR'


class SearchResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    url: str
    snippet: str
    publishedAt: date | None = None


class FreshnessIntent(BaseModel):
    requiresRealtimeSearch: bool
    reason: str | None = None


class RealtimePolicyHit(SearchResult):
    hitId: str
    domain: str
    department: str | None = None
    retrievedAt: datetime
    matchedKeywords: list[str] = Field(default_factory=list)
    official: bool = True
    relatedPolicyId: str | None = None
    freshnessReason: str
