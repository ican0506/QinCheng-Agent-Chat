from __future__ import annotations

from pathlib import Path

from app.policy.repository import PolicyRepository
from app.rag.models import RagDocument


class RagDocumentLoader:
    """仅加载与已核验 PolicyRecord 对应的本地原文 Markdown。"""

    def __init__(self, repository: PolicyRepository, raw_directory: Path) -> None:
        self._repository = repository
        self._raw_directory = raw_directory

    def load(self) -> list[RagDocument]:
        documents: list[RagDocument] = []
        for record in self._repository.filter():
            raw_path = self._raw_directory / f"{record.policyId}.md"
            markdown = raw_path.read_text(encoding="utf-8")
            documents.append(RagDocument(
                policyId=record.policyId,
                policyName=record.name,
                region=record.region,
                department=record.department,
                sourceUrl=record.sourceUrl or "",
                validityStatus=record.validityStatus.value,
                lastVerifiedAt=record.lastVerifiedAt,
                topics=tuple(record.topics),
                targetGroups=tuple(record.targetGroups),
                markdown=markdown,
                applicationStatus=record.applicationStatus.value,
            ))
        return documents
