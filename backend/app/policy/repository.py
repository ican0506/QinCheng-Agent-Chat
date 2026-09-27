from __future__ import annotations

import json
from pathlib import Path

from app.policy.models import PolicyRecord


class PolicyRepository:
    """加载本地 JSON 并提供不包含业务判断的确定性筛选。"""

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self._policies = self._load()

    def _load(self) -> list[PolicyRecord]:
        with self._data_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, list):
            raise ValueError("policies.json 必须是政策数组")
        return [PolicyRecord.model_validate(item) for item in raw]

    def get_by_id(self, policy_id: str) -> PolicyRecord | None:
        return next((item for item in self._policies if item.policyId == policy_id), None)

    def filter_by_region(self, region: str) -> list[PolicyRecord]:
        return self.filter(region=region)

    def filter_by_topic(self, topic: str) -> list[PolicyRecord]:
        return self.filter(topic=topic)

    def filter_by_target_group(self, target_group: str) -> list[PolicyRecord]:
        return self.filter(target_group=target_group)

    def filter(
        self,
        *,
        region: str | None = None,
        topic: str | None = None,
        target_group: str | None = None,
    ) -> list[PolicyRecord]:
        return [
            item
            for item in self._policies
            if (region is None or item.region == region)
            and (topic is None or topic in item.topics)
            and (target_group is None or target_group in item.targetGroups)
        ]
