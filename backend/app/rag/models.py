from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RagDocument:
    policyId: str
    policyName: str
    region: str
    department: str
    sourceUrl: str
    validityStatus: str
    lastVerifiedAt: date | None
    topics: tuple[str, ...]
    targetGroups: tuple[str, ...]
    markdown: str
    applicationStatus: str = "UNKNOWN"


@dataclass(frozen=True)
class RagChunk:
    policyId: str
    policyName: str
    region: str
    department: str
    sourceUrl: str
    validityStatus: str
    lastVerifiedAt: date | None
    topics: tuple[str, ...]
    targetGroups: tuple[str, ...]
    chunkId: str
    heading: str
    chunkText: str
    applicationStatus: str = "UNKNOWN"


@dataclass(frozen=True)
class RagSearchHit:
    policyId: str
    policyName: str
    region: str
    department: str
    sourceUrl: str
    validityStatus: str
    lastVerifiedAt: date | None
    chunkId: str
    chunkText: str
    score: float
    heading: str
