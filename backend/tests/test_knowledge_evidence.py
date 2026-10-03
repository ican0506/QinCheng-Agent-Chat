from __future__ import annotations

from pathlib import Path

from app.agent.tools.dify_policy_sources import DifyPolicySourceCatalog
from app.agent.tools.dify_policy import DifySearchOutcome
from app.agent.models import GovernmentAgentState, KnowledgeEvidence
from app.agent.nodes.policy_search import PolicySearchNode
from app.models.chat import UserProfile
from app.services.chat_service import ChatService
from app.services.policy_query_context import PolicyQueryMode
import asyncio


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = BACKEND_ROOT / "data" / "dify_policy_sources.json"


def catalog() -> DifyPolicySourceCatalog:
    return DifyPolicySourceCatalog.from_path(CATALOG_PATH)


def test_catalog_maps_a_knowledge_document_id_to_verified_source_metadata() -> None:
    source = catalog().get_by_knowledge_id(
        "dify-v2-suzhou-entrepreneurship-driven-employment-subsidy"
    )

    assert source is not None
    assert source.policyName == "创业带动就业补贴"
    assert source.structuredPolicyId is None
    assert source.currentness == "UNKNOWN"
    assert source.sourceUrl.startswith("https://")


def test_catalog_uses_exact_document_name_only_as_knowledge_id_fallback() -> None:
    source = catalog().get_by_document_name("创业带动就业补贴.md")

    assert source is not None
    assert source.knowledgeId == "dify-v2-suzhou-entrepreneurship-driven-employment-subsidy"
    assert catalog().get_by_document_name("创业带动就业补贴（转载）.md") is None


def test_catalog_ignores_unknown_knowledge_ids() -> None:
    assert catalog().get_by_knowledge_id("knowledge-only-unknown") is None


def test_policy_search_node_keeps_request_scoped_knowledge_evidence() -> None:
    class OutcomeTool:
        async def search_outcome(self, profile, message):
            return DifySearchOutcome(
                structuredCandidates=[],
                knowledgeEvidences=[KnowledgeEvidence(
                    knowledgeId="knowledge-only-test",
                    policyName="创业带动就业补贴",
                    sourceUrl="https://www.suzhou.gov.cn/example",
                    currentness="UNKNOWN",
                    chunkText="官方正文",
                    score=0.9,
                )],
            )

    state = GovernmentAgentState(
        sessionId="session-a",
        userMessage="创业带动就业补贴需要什么条件？",
        userProfile=UserProfile(),
    )
    result = asyncio.run(PolicySearchNode(OutcomeTool()).execute(state))

    assert result.candidatePolicies == []
    assert [item.knowledgeId for item in result.knowledgeEvidences] == ["knowledge-only-test"]


def test_fact_query_fallback_answers_knowledge_only_evidence_with_unknown_notice() -> None:
    state = GovernmentAgentState(
        sessionId="session-a",
        userMessage="创业带动就业补贴需要什么条件？",
        userProfile=UserProfile(),
        queryMode=PolicyQueryMode.FACT_QUERY,
        knowledgeEvidences=[KnowledgeEvidence(
            knowledgeId="knowledge-only-test",
            policyName="创业带动就业补贴",
            sourceUrl="https://www.suzhou.gov.cn/example",
            currentness="UNKNOWN",
            chunkText="创业后带动其他劳动者就业的官方条件。",
            score=0.9,
        )],
    )

    reply = ChatService._local_fallback_reply(state)

    assert "创业带动就业补贴" in reply
    assert "https://www.suzhou.gov.cn/example" in reply
    assert "当前有效性尚未完成结构化确认" in reply
    assert "PASS" not in reply
    assert "FAIL" not in reply


def test_personalized_query_does_not_claim_knowledge_only_eligibility() -> None:
    state = GovernmentAgentState(
        sessionId="session-a",
        userMessage="我符合创业带动就业补贴吗？",
        userProfile=UserProfile(),
        queryMode=PolicyQueryMode.PERSONALIZED_QUERY,
        knowledgeEvidences=[KnowledgeEvidence(
            knowledgeId="knowledge-only-test",
            policyName="创业带动就业补贴",
            sourceUrl="https://www.suzhou.gov.cn/example",
            currentness="UNKNOWN",
            chunkText="官方条件。",
            score=0.9,
        )],
    )

    reply = ChatService._local_fallback_reply(state)

    assert "尚未进入结构化资格规则库" in reply
    assert "PASS" not in reply
    assert "FAIL" not in reply


def test_historical_knowledge_evidence_has_a_non_current_notice() -> None:
    state = GovernmentAgentState(
        sessionId="session-a",
        userMessage="历史通知",
        userProfile=UserProfile(),
        queryMode=PolicyQueryMode.FACT_QUERY,
        knowledgeEvidences=[KnowledgeEvidence(
            knowledgeId="knowledge-only-history",
            policyName="历史补贴通知",
            sourceUrl="https://www.suzhou.gov.cn/example",
            currentness="HISTORICAL",
            chunkText="历史通知正文。",
            score=0.9,
        )],
    )

    assert "历史政策或历史通知" in ChatService._local_fallback_reply(state)
    assert "不能据此认为当前仍开放" in ChatService._local_fallback_reply(state)


def test_concurrent_policy_search_states_do_not_share_knowledge_evidence() -> None:
    class OutcomeTool:
        async def search_outcome(self, profile, message):
            return DifySearchOutcome([], [KnowledgeEvidence(
                knowledgeId=message,
                policyName=message,
                sourceUrl="https://www.suzhou.gov.cn/example",
                currentness="UNKNOWN",
                chunkText=message,
                score=0.9,
            )])

    async def run() -> tuple[GovernmentAgentState, GovernmentAgentState]:
        node = PolicySearchNode(OutcomeTool())
        left = GovernmentAgentState(sessionId="left", userMessage="left", userProfile=UserProfile())
        right = GovernmentAgentState(sessionId="right", userMessage="right", userProfile=UserProfile())
        return await asyncio.gather(node.execute(left), node.execute(right))

    left, right = asyncio.run(run())
    assert [item.knowledgeId for item in left.knowledgeEvidences] == ["left"]
    assert [item.knowledgeId for item in right.knowledgeEvidences] == ["right"]
