from __future__ import annotations

import hashlib
import re

from app.agent.models import PolicyCandidate
from app.models.chat import MaterialCheckResult, MaterialStatus
from app.policy.repository import PolicyRepository


class MaterialCheckTool:
    """基于已核验政策材料和用户明确陈述生成确定性预检结果。"""

    _non_concrete_markers = ("以经办渠道", "以最新", "当前要求为准", "具体材料")
    _missing_markers = ("还没有", "没准备", "没有", "未准备")
    _ready_markers = ("已经准备好", "准备好了", "准备好", "已准备", "有了", "我有", "已有")

    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

    async def check(
        self,
        message: str,
        policies: list[PolicyCandidate],
        declarations: dict[str, bool],
    ) -> tuple[list[MaterialCheckResult], dict[str, bool]]:
        requirements = self._requirements(policies)
        updated = dict(declarations)
        for policy_id, material_name, material_id in requirements:
            stated = self._statement_for(message, material_name)
            if stated is not None:
                updated[material_id] = stated
        return [self._result(policy_id, name, material_id, updated.get(material_id)) for policy_id, name, material_id in requirements], updated

    def _requirements(self, policies: list[PolicyCandidate]) -> list[tuple[str, str, str]]:
        requirements: list[tuple[str, str, str]] = []
        for policy in policies:
            record = self._repository.get_by_id(policy.policyId)
            if record is None:
                continue
            for material_name in record.requiredMaterials:
                if self.is_concrete_material(material_name):
                    requirements.append((record.policyId, material_name, self.material_id(record.policyId, material_name)))
        return requirements

    @classmethod
    def is_concrete_material(cls, material_name: str) -> bool:
        cleaned = material_name.strip()
        return bool(cleaned) and not any(marker in cleaned for marker in cls._non_concrete_markers)

    @staticmethod
    def normalize_material_name(material_name: str) -> str:
        return re.sub(r"[\s《》〈〉“”‘’\"']+", "", material_name).lower()

    @classmethod
    def material_id(cls, policy_id: str, material_name: str) -> str:
        normalized = cls.normalize_material_name(material_name)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"{policy_id}:{digest}"

    @classmethod
    def _statement_for(cls, message: str, material_name: str) -> bool | None:
        compact_message = cls.normalize_material_name(message)
        aliases = {
            cls.normalize_material_name(alias)
            for alias in (material_name, material_name.replace("证书", "证"), material_name.split("或", 1)[0])
        }
        if not any(alias and alias in compact_message for alias in aliases):
            return None
        if any(marker in compact_message for marker in cls._missing_markers):
            return False
        if any(marker in compact_message for marker in cls._ready_markers):
            return True
        return None

    @staticmethod
    def _result(policy_id: str, material_name: str, material_id: str, declaration: bool | None) -> MaterialCheckResult:
        requires_review = "证明" in material_name or "认定" in material_name
        if declaration is False:
            return MaterialCheckResult(materialId=material_id, policyId=policy_id, materialName=material_name, status=MaterialStatus.MISSING, reason="用户明确表示尚未准备该材料。", userProvided=True)
        if requires_review:
            return MaterialCheckResult(materialId=material_id, policyId=policy_id, materialName=material_name, status=MaterialStatus.MANUAL_REVIEW, reason="该证明材料的内容和有效性需由经办机构或人工核验。", userProvided=declaration is True, needsManualReview=True)
        if declaration is True:
            return MaterialCheckResult(materialId=material_id, policyId=policy_id, materialName=material_name, status=MaterialStatus.READY, reason="用户明确表示已准备该材料。", userProvided=True)
        return MaterialCheckResult(materialId=material_id, policyId=policy_id, materialName=material_name, status=MaterialStatus.UNKNOWN, reason="尚未收到用户对该材料准备情况的明确说明。")
