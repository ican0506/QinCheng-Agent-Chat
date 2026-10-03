from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DifyPolicySource:
    knowledgeId: str
    policyName: str
    difyDocumentName: str
    sourceUrl: str
    currentness: str
    structuredPolicyId: str | None
    classification: str


class DifyPolicySourceCatalog:
    """只读知识资产目录；不参与结构化资格或政策数据写入。"""

    def __init__(self, sources: list[DifyPolicySource]) -> None:
        self._by_knowledge_id = {source.knowledgeId: source for source in sources}
        self._by_document_name = {source.difyDocumentName: source for source in sources}

    @classmethod
    def from_path(cls, path: Path) -> DifyPolicySourceCatalog:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources = [
            DifyPolicySource(
                knowledgeId=item["knowledgeId"],
                policyName=item["policyName"],
                difyDocumentName=item["difyDocumentName"],
                sourceUrl=item["sourceUrl"],
                currentness=item["currentness"],
                structuredPolicyId=item["structuredPolicyId"],
                classification=item["classification"],
            )
            for item in payload["sources"]
        ]
        return cls(sources)

    def get_by_knowledge_id(self, knowledge_id: str) -> DifyPolicySource | None:
        return self._by_knowledge_id.get(knowledge_id)

    def get_by_document_name(self, document_name: str | None) -> DifyPolicySource | None:
        return self._by_document_name.get(document_name or "")
