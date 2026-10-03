from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx

from app.agent.models import KnowledgeEvidence, PolicyCandidate
from app.agent.tools.base import PolicySearchTool
from app.agent.tools.dify_policy_sources import DifyPolicySourceCatalog
from app.models.chat import UserProfile
from app.policy.models import PolicyRecord
from app.policy.repository import PolicyRepository


logger = logging.getLogger("uvicorn.error")


class DifyPolicySearchError(RuntimeError):
    def __init__(self, reason: str, *, status_code: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True)
class DifyRetrievalRecord:
    content: str
    score: float
    document_name: str | None


@dataclass(frozen=True)
class DifySearchOutcome:
    structuredCandidates: list[PolicyCandidate]
    knowledgeEvidences: list[KnowledgeEvidence]


class DifyPolicySearchTool:
    """使用 Dify Knowledge 召回已入库政策；结构化事实仍只来自 PolicyRepository。"""

    _policy_id_pattern = re.compile(
        r"(?:^|\n)\s*(?:政策ID|policyId)\s*[:：]\s*([A-Za-z0-9._-]+)",
        re.IGNORECASE,
    )
    _knowledge_id_pattern = re.compile(
        r"(?:^|\n)\s*知识文档ID\s*[:：]\s*([A-Za-z0-9._-]+)",
        re.IGNORECASE,
    )
    _document_name_aliases = {
        "求职创业补贴_2026届历史通知": "suzhou-job-seeking-subsidy-2026",
    }

    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        dataset_id: str,
        api_key: str,
        timeout_seconds: float,
        top_k: int,
        repository: PolicyRepository,
        fallback: PolicySearchTool,
        source_catalog: DifyPolicySourceCatalog | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._enabled = enabled
        self._base_url = base_url.rstrip("/")
        self._dataset_id = dataset_id.strip()
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._top_k = top_k
        self._repository = repository
        self._fallback = fallback
        self._source_catalog = source_catalog
        self._client = client

    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]:
        return (await self.search_outcome(profile, message)).structuredCandidates

    async def search_outcome(self, profile: UserProfile, message: str) -> DifySearchOutcome:
        started = perf_counter()
        if not self._enabled:
            return DifySearchOutcome(
                await self._fallback_with_log(profile, message, "disabled", started), []
            )
        if not self._dataset_id or not self._api_key.strip():
            return DifySearchOutcome(
                await self._fallback_with_log(profile, message, "missing_config", started), []
            )

        try:
            records = await self._retrieve(message)
        except DifyPolicySearchError as exc:
            return DifySearchOutcome(
                await self._fallback_with_log(
                    profile, message, exc.reason, started, exc.status_code
                ), []
            )

        candidates, evidences, unmapped = self._outcome_from_records(records)
        if candidates or evidences:
            self._log(
                elapsed_ms=(perf_counter() - started) * 1000,
                status_code=200,
                records_count=len(records),
                mapped_policy_ids=[candidate.policyId for candidate in candidates],
                fallback_reason=None,
            )
            return DifySearchOutcome(candidates, evidences)
        return DifySearchOutcome(
            await self._fallback_with_log(
                profile,
                message,
                "unmapped" if unmapped else "no_match",
                started,
                200,
                records_count=len(records),
            ), []
        )

    async def _retrieve(self, message: str) -> list[DifyRetrievalRecord]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            response = await client.post(
                f"{self._base_url}/datasets/{self._dataset_id}/retrieve",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": message,
                    "retrieval_model": {
                        "search_method": "semantic_search",
                        "reranking_enable": False,
                        "top_k": self._top_k,
                        "score_threshold_enabled": False,
                    },
                },
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise DifyPolicySearchError("timeout") from exc
        except httpx.RequestError as exc:
            raise DifyPolicySearchError("network_error") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code >= 400:
            if response.status_code in {401, 403, 429}:
                reason = f"http_{response.status_code}"
            elif response.status_code >= 500:
                reason = "http_5xx"
            else:
                reason = "http_error"
            raise DifyPolicySearchError(reason, status_code=response.status_code)
        try:
            body = response.json()
        except ValueError as exc:
            raise DifyPolicySearchError("invalid_json", status_code=response.status_code) from exc
        if not isinstance(body, dict) or not isinstance(body.get("records"), list):
            raise DifyPolicySearchError("invalid_schema", status_code=response.status_code)
        return [parsed for item in body["records"] if (parsed := self._parse_record(item)) is not None]

    @staticmethod
    def _parse_record(item: Any) -> DifyRetrievalRecord | None:
        if not isinstance(item, dict):
            return None
        segment = item.get("segment")
        content = segment.get("content") if isinstance(segment, dict) else item.get("content")
        score = item.get("score")
        if not isinstance(content, str) or not content.strip() or not isinstance(score, (int, float)):
            return None
        document = item.get("document")
        document_name = item.get("document_name")
        if document_name is None and isinstance(document, dict):
            document_name = document.get("name")
        return DifyRetrievalRecord(
            content=content.strip(),
            score=float(score),
            document_name=document_name.strip() if isinstance(document_name, str) and document_name.strip() else None,
        )

    def _outcome_from_records(
        self, records: list[DifyRetrievalRecord]
    ) -> tuple[list[PolicyCandidate], list[KnowledgeEvidence], bool]:
        best_records: dict[str, tuple[PolicyRecord, DifyRetrievalRecord]] = {}
        best_evidences: dict[str, KnowledgeEvidence] = {}
        saw_unmapped = False
        for retrieval_record in records:
            evidence = self._knowledge_evidence_for(retrieval_record)
            if evidence is not None:
                existing_evidence = best_evidences.get(evidence.knowledgeId)
                if existing_evidence is None or evidence.score > existing_evidence.score:
                    best_evidences[evidence.knowledgeId] = evidence
                continue
            policy_record = self._policy_record_for(retrieval_record)
            if policy_record is None:
                saw_unmapped = True
                continue
            existing = best_records.get(policy_record.policyId)
            if existing is None or retrieval_record.score > existing[1].score:
                best_records[policy_record.policyId] = (policy_record, retrieval_record)

        ordered = sorted(
            best_records.values(), key=lambda item: (-item[1].score, item[0].policyId)
        )
        evidences = sorted(best_evidences.values(), key=lambda item: (-item.score, item.knowledgeId))
        return [self._candidate(record, hit) for record, hit in ordered], evidences, saw_unmapped

    def _knowledge_evidence_for(
        self, retrieval_record: DifyRetrievalRecord
    ) -> KnowledgeEvidence | None:
        if self._source_catalog is None:
            return None
        match = self._knowledge_id_pattern.search(retrieval_record.content)
        source = (
            self._source_catalog.get_by_knowledge_id(match.group(1).strip())
            if match is not None
            else self._source_catalog.get_by_document_name(retrieval_record.document_name)
        )
        if source is None or source.structuredPolicyId is not None:
            return None
        return KnowledgeEvidence(
            knowledgeId=source.knowledgeId,
            policyName=source.policyName,
            sourceUrl=source.sourceUrl,
            currentness=source.currentness,
            chunkText=retrieval_record.content,
            score=retrieval_record.score,
        )

    def _policy_record_for(self, retrieval_record: DifyRetrievalRecord) -> PolicyRecord | None:
        match = self._policy_id_pattern.search(retrieval_record.content)
        if match is not None:
            return self._repository.get_by_id(match.group(1).strip())
        if retrieval_record.document_name is None:
            return None
        normalized_name = self._normalize_document_name(retrieval_record.document_name)
        alias_policy_id = self._document_name_aliases.get(normalized_name)
        if alias_policy_id is not None:
            return self._repository.get_by_id(alias_policy_id)
        exact_matches = [
            record
            for record in self._repository.filter()
            if self._normalize_document_name(record.name) == normalized_name
        ]
        return exact_matches[0] if len(exact_matches) == 1 else None

    @staticmethod
    def _normalize_document_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).strip()
        normalized = re.sub(r"\.md$", "", normalized, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def _candidate(record: PolicyRecord, hit: DifyRetrievalRecord) -> PolicyCandidate:
        snippet = " ".join(hit.content.split())[:160]
        return PolicyCandidate(
            policyId=record.policyId,
            name=record.name,
            region=record.region,
            department=record.department,
            summary=record.summary,
            effectiveDate=record.effectiveDate or "",
            expiryDate=record.expiryDate,
            sourceUrl=record.sourceUrl or "",
            matchReason=f"Dify 知识库命中原文片段（相关度 {hit.score:.2f}）：{snippet}",
            conditions=[condition.description for condition in record.conditions],
            requiredMaterials=record.requiredMaterials,
            process=record.process,
            isMock=False,
        )

    async def _fallback_with_log(
        self,
        profile: UserProfile,
        message: str,
        reason: str,
        started: float,
        status_code: int | None = None,
        records_count: int = 0,
    ) -> list[PolicyCandidate]:
        result = await self._fallback.search(profile, message)
        self._log(
            elapsed_ms=(perf_counter() - started) * 1000,
            status_code=status_code,
            records_count=records_count,
            mapped_policy_ids=[],
            fallback_reason=reason,
        )
        return result

    @staticmethod
    def _log(
        *,
        elapsed_ms: float,
        status_code: int | None,
        records_count: int,
        mapped_policy_ids: list[str],
        fallback_reason: str | None,
    ) -> None:
        logger.info(
            "dify_policy_search provider=dify elapsed_ms=%d status_code=%s records_count=%d "
            "mapped_count=%d mapped_policy_ids=%s fallback_reason=%s",
            elapsed_ms,
            status_code if status_code is not None else "none",
            records_count,
            len(mapped_policy_ids),
            mapped_policy_ids,
            fallback_reason,
        )
