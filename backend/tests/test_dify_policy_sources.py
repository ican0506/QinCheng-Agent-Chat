from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from app.policy.repository import PolicyRepository


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = BACKEND_ROOT / "data" / "dify_policy_sources.json"
POLICIES_PATH = BACKEND_ROOT / "data" / "policies" / "policies.json"
VALID_CURRENTNESS = {"CURRENT", "HISTORICAL", "UNKNOWN"}
VALID_DIFY_STATUSES = {"available", "planned"}


def load_sources() -> list[dict]:
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload["sources"], list)
    return payload["sources"]


def test_dify_policy_sources_are_a_complete_validated_local_catalog() -> None:
    sources = load_sources()
    repository = PolicyRepository(POLICIES_PATH)

    assert len(sources) == 20
    assert {source["difyStatus"] for source in sources} <= VALID_DIFY_STATUSES
    assert sum(source["difyStatus"] == "available" for source in sources) == 12
    assert sum(source["difyStatus"] == "planned" for source in sources) == 8

    knowledge_ids = [source["knowledgeId"] for source in sources]
    names_and_urls = [(source["policyName"], source["sourceUrl"]) for source in sources]
    assert len(knowledge_ids) == len(set(knowledge_ids))
    assert len(names_and_urls) == len(set(names_and_urls))

    for source in sources:
        assert source["policyName"].strip()
        assert source["difyDocumentName"].strip()
        assert source["currentness"] in VALID_CURRENTNESS
        assert urlparse(source["sourceUrl"]).scheme == "https"

        structured_policy_id = source["structuredPolicyId"]
        if source["classification"] == "knowledge-only":
            assert structured_policy_id is None
        elif structured_policy_id is not None:
            assert repository.get_by_id(structured_policy_id) is not None
