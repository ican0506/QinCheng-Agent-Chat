"""把用户明确点名的政策收敛为结构化目标；不参与资格判断。"""
from __future__ import annotations

from app.policy.repository import PolicyRepository


class TargetPolicyResolver:
    def __init__(self, repository: PolicyRepository | None) -> None:
        self._repository = repository

    def resolve(self, message: str) -> str | None:
        if self._repository is None:
            return None
        normalized = message.replace("社保", "社会保险")
        for record in self._repository.filter():
            if record.name in normalized:
                return record.policyId
            if record.policyId == "suzhou-startup-social-2021" and "创业社会保险补贴" in normalized:
                return record.policyId
            if record.policyId == "suzhou-flexible-social-2021" and "灵活就业社会保险补贴" in normalized:
                return record.policyId
            if record.policyId == "suzhou-employment-internship-2024" and "就业见习" in normalized:
                return record.policyId
        return None
