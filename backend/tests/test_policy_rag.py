from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.rag_policy import RagPolicySearchTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.rag.chunker import MarkdownPolicyChunker
from app.rag.loader import RagDocumentLoader
from app.rag.models import RagChunk
from app.rag.retriever import InMemoryRagRetriever


def repository() -> PolicyRepository:
    backend_root = Path(__file__).resolve().parents[1]
    return PolicyRepository(backend_root / "data" / "policies" / "policies.json")


def retriever() -> InMemoryRagRetriever:
    backend_root = Path(__file__).resolve().parents[1]
    documents = RagDocumentLoader(repository(), backend_root / "data" / "policies" / "raw").load()
    return InMemoryRagRetriever(MarkdownPolicyChunker().chunk_documents(documents))


def profile() -> UserProfile:
    return UserProfile(city="苏州市", education="本科", graduationYear=2026, employmentStatus="创业中")


def test_loader_and_chunker_keep_verified_policy_metadata_and_heading() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    documents = RagDocumentLoader(repository(), backend_root / "data" / "policies" / "raw").load()
    chunks = MarkdownPolicyChunker().chunk_documents(documents)

    assert len(documents) == 5
    assert chunks
    assert all(chunk.policyId and chunk.policyName and chunk.region and chunk.department for chunk in chunks)
    assert all(chunk.sourceUrl and chunk.validityStatus and chunk.lastVerifiedAt for chunk in chunks)
    assert all(chunk.chunkId and chunk.heading and chunk.chunkText for chunk in chunks)
    assert {chunk.policyId for chunk in chunks} == {record.policyId for record in repository().filter()}


def test_startup_query_ranks_one_time_startup_subsidy_highly() -> None:
    hits = retriever().search("苏州毕业生创业有什么补贴", region="苏州市", topic="创业补贴", top_k=3)

    assert hits
    assert any(hit.policyId == "suzhou-startup-one-time-2023" for hit in hits)


def test_social_insurance_queries_retrieve_relevant_active_policies() -> None:
    startup_hits = retriever().search("创业以后自己交社保有补贴吗", region="苏州市", topic="社会保险", top_k=3)
    flexible_hits = retriever().search("离校以后灵活就业自己缴社保", region="苏州市", topic="社会保险", top_k=3)

    assert any(hit.policyId == "suzhou-startup-social-2021" for hit in startup_hits)
    assert flexible_hits[0].policyId == "suzhou-flexible-social-2021"


def test_irrelevant_query_does_not_force_policy_results() -> None:
    hits = retriever().search("周末去哪里看电影比较好", region="苏州市", top_k=3)

    assert hits == []


def test_region_filter_and_active_priority_are_applied_before_top_k() -> None:
    active = RagChunk(
        policyId="active", policyName="当前创业补贴", region="苏州市", department="人社局",
        sourceUrl="https://example.com/active", validityStatus="ACTIVE", lastVerifiedAt=date(2026, 9, 28),
        topics=("创业补贴",), targetGroups=(), chunkId="active-1", heading="当前口径", chunkText="创业补贴 社保 支持",
    )
    historical = RagChunk(
        policyId="historical", policyName="历史创业补贴", region="苏州市", department="人社局",
        sourceUrl="https://example.com/historical", validityStatus="HISTORICAL", lastVerifiedAt=date(2026, 9, 28),
        topics=("创业补贴",), targetGroups=(), chunkId="historical-1", heading="历史口径", chunkText="创业补贴 社保 支持",
    )
    other_region = RagChunk(
        policyId="other", policyName="外地创业补贴", region="无锡市", department="人社局",
        sourceUrl="https://example.com/other", validityStatus="ACTIVE", lastVerifiedAt=date(2026, 9, 28),
        topics=("创业补贴",), targetGroups=(), chunkId="other-1", heading="当前口径", chunkText="创业补贴 社保 支持",
    )
    index = InMemoryRagRetriever([historical, other_region, active])

    hits = index.search("创业补贴社保", region="苏州市", topic="创业补贴", top_k=3)

    assert [hit.policyId for hit in hits] == ["active", "historical"]


def test_rag_tool_deduplicates_policy_candidates_and_keeps_source_traceability() -> None:
    tool = RagPolicySearchTool(retriever(), repository(), LocalPolicySearchTool(repository()))
    candidates = asyncio.run(tool.search(profile(), "苏州毕业生创业有什么补贴"))

    assert candidates
    assert len({candidate.policyId for candidate in candidates}) == len(candidates)
    assert all(candidate.sourceUrl and "RAG 命中" in candidate.matchReason for candidate in candidates)
    assert all(repository().get_by_id(candidate.policyId).sourceUrl == candidate.sourceUrl for candidate in candidates)


def test_rag_failure_falls_back_to_local_policy_search() -> None:
    class BrokenRetriever:
        def search(self, *args, **kwargs):
            raise RuntimeError("index unavailable")

    local_tool = LocalPolicySearchTool(repository())
    tool = RagPolicySearchTool(BrokenRetriever(), repository(), local_tool)
    candidates = asyncio.run(tool.search(profile(), "创业补贴"))

    assert candidates
    assert all(candidate.isMock is False for candidate in candidates)
