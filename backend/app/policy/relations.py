from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.agent.models import PolicyRelationType


class PolicyRelationConfig(BaseModel):
    sourcePolicyId: str
    targetPolicyId: str
    relationType: PolicyRelationType
    reason: str
    policyEvidence: str | None = None


class PolicyRelationRepository:
    """加载人工核验的显式政策关系配置，不推断关系。"""

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self._relations = self._load()

    def _load(self) -> list[PolicyRelationConfig]:
        with self._data_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, list):
            raise ValueError("policy_relations.json 必须是关系数组")
        return [PolicyRelationConfig.model_validate(item) for item in raw]

    def all(self) -> list[PolicyRelationConfig]:
        return list(self._relations)
