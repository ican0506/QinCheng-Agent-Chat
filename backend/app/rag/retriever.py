from __future__ import annotations

from collections import Counter
from math import log, sqrt
from app.rag.models import RagChunk, RagSearchHit


class InMemoryRagRetriever:
    """采用元数据筛选后进行中文字符 n-gram TF-IDF 相关性排序的本地检索器。"""

    minimum_score = 0.04

    def __init__(self, chunks: list[RagChunk]) -> None:
        self._chunks = chunks
        self._term_frequencies = [self._term_frequency(self._searchable_text(chunk)) for chunk in chunks]
        document_frequency = Counter(term for terms in self._term_frequencies for term in terms)
        total = len(chunks)
        self._idf = {term: log((total + 1) / (count + 1)) + 1 for term, count in document_frequency.items()}

    def metadata_filter(
        self,
        *,
        region: str | None = None,
        topic: str | None = None,
        target_group: str | None = None,
        validity_statuses: set[str] | None = None,
        policy_ids: set[str] | None = None,
    ) -> list[tuple[RagChunk, Counter[str]]]:
        return [
            (chunk, terms)
            for chunk, terms in zip(self._chunks, self._term_frequencies, strict=True)
            if (region is None or chunk.region == region)
            and (topic is None or topic in chunk.topics)
            and (target_group is None or target_group in chunk.targetGroups)
            and (validity_statuses is None or chunk.validityStatus in validity_statuses)
            and (policy_ids is None or chunk.policyId in policy_ids)
        ]

    def search(
        self,
        query: str,
        *,
        region: str | None = None,
        topic: str | None = None,
        target_group: str | None = None,
        validity_statuses: set[str] | None = None,
        policy_ids: set[str] | None = None,
        include_historical: bool = False,
        top_k: int = 5,
    ) -> list[RagSearchHit]:
        query_terms = self._term_frequency(query)
        if not query_terms:
            return []
        ranked: list[tuple[int, float, RagSearchHit]] = []
        for chunk, terms in self.metadata_filter(
            region=region,
            topic=topic,
            target_group=target_group,
            validity_statuses=validity_statuses,
            policy_ids=policy_ids,
        ):
            score = self._cosine_similarity(query_terms, terms)
            if score < self.minimum_score:
                continue
            hit = RagSearchHit(
                policyId=chunk.policyId,
                policyName=chunk.policyName,
                region=chunk.region,
                department=chunk.department,
                sourceUrl=chunk.sourceUrl,
                validityStatus=chunk.validityStatus,
                lastVerifiedAt=chunk.lastVerifiedAt,
                chunkId=chunk.chunkId,
                chunkText=chunk.chunkText,
                score=round(score, 4),
                heading=chunk.heading,
            )
            ranked.append((self.temporal_rank(chunk.validityStatus, chunk.applicationStatus, include_historical), score, hit))
        ranked.sort(key=lambda item: (item[0], -item[1], item[2].policyId, item[2].chunkId))
        return [hit for _, _, hit in ranked[:top_k]]

    @staticmethod
    def temporal_rank(validity_status: str, application_status: str, include_historical: bool) -> int:
        reference = validity_status in {"HISTORICAL", "EXPIRED"} or application_status == "CLOSED"
        if include_historical:
            return 0 if reference else 1
        if reference:
            return 2
        if validity_status == "ACTIVE":
            return 0
        return 1

    @staticmethod
    def _searchable_text(chunk: RagChunk) -> str:
        return f"{chunk.policyName} {chunk.heading} {chunk.chunkText} {' '.join(chunk.topics)} {' '.join(chunk.targetGroups)}"

    @staticmethod
    def _term_frequency(text: str) -> Counter[str]:
        normalized = "".join(character.lower() for character in text if character.isalnum())
        if len(normalized) < 2:
            return Counter(normalized)
        terms = [normalized[index:index + width] for width in (2, 3) for index in range(len(normalized) - width + 1)]
        return Counter(terms)

    def _cosine_similarity(self, query_terms: Counter[str], document_terms: Counter[str]) -> float:
        query_weights = self._weights(query_terms)
        document_weights = self._weights(document_terms)
        numerator = sum(query_weights[term] * document_weights.get(term, 0.0) for term in query_weights)
        denominator = sqrt(sum(weight * weight for weight in query_weights.values())) * sqrt(sum(weight * weight for weight in document_weights.values()))
        return numerator / denominator if denominator else 0.0

    def _weights(self, terms: Counter[str]) -> dict[str, float]:
        total = sum(terms.values())
        return {term: count / total * self._idf.get(term, 0.0) for term, count in terms.items()}
