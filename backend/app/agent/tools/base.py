from __future__ import annotations

from typing import Protocol

from app.agent.models import EligibilityResult, OverallPlan, PolicyCandidate, PolicyRelation
from app.models.chat import UserProfile


class PolicySearchTool(Protocol):
    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]: ...


class EligibilityTool(Protocol):
    async def check(
        self, profile: UserProfile, policies: list[PolicyCandidate]
    ) -> list[EligibilityResult]: ...


class PolicyCompareTool(Protocol):
    async def compare(
        self, policies: list[PolicyCandidate], eligibility: list[EligibilityResult]
    ) -> list[PolicyRelation]: ...


class PlanTool(Protocol):
    async def build_plan(
        self,
        policies: list[PolicyCandidate],
        eligibility: list[EligibilityResult],
        relations: list[PolicyRelation],
    ) -> OverallPlan: ...
