from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.agent.tools.local_policy import LocalPolicySearchTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository


def write_policies(path, policies: list[dict]) -> None:
    path.write_text(json.dumps(policies, ensure_ascii=False), encoding="utf-8")


def policy(policy_id: str, *, region: str = "杭州", topics: list[str] | None = None, target_groups: list[str] | None = None) -> dict:
    return {
        "policyId": policy_id,
        "name": f"{policy_id}（待核验）",
        "region": region,
        "department": "待人工核验",
        "summary": "仅作为本地政策数据结构占位，不代表真实官方政策。",
        "publishedDate": None,
        "effectiveDate": None,
        "expiryDate": None,
        "sourceUrl": None,
        "targetGroups": target_groups or ["应届毕业生"],
        "topics": topics or ["创业补贴"],
        "conditions": [{"conditionId": "education", "field": "education", "operator": "in", "value": ["本科", "硕士"], "description": "学历条件待人工核验。", "policyEvidence": "待补充官方政策依据。"}],
        "requiredMaterials": ["待人工核验"],
        "process": ["待人工核验"],
        "isVerified": False,
    }


def test_repository_rejects_missing_data_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        PolicyRepository(tmp_path / "missing.json")


def test_project_policies_json_loads_only_unverified_placeholder_records() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )

    records = repository.filter()
    assert len(records) == 6
    assert all(record.isVerified is False and record.sourceUrl is None for record in records)


def test_repository_loads_json_and_gets_by_id(tmp_path) -> None:
    file_path = tmp_path / "policies.json"
    write_policies(file_path, [policy("POLICY-001")])

    repository = PolicyRepository(file_path)

    assert repository.get_by_id("POLICY-001").policyId == "POLICY-001"
    assert repository.get_by_id("MISSING") is None
    assert repository.get_by_id("POLICY-001").isVerified is False
    assert repository.get_by_id("POLICY-001").sourceUrl is None


def test_repository_filters_by_region_topic_target_group_and_combination(tmp_path) -> None:
    file_path = tmp_path / "policies.json"
    write_policies(file_path, [
        policy("POLICY-001", region="杭州", topics=["创业补贴"], target_groups=["应届毕业生"]),
        policy("POLICY-002", region="杭州", topics=["就业补贴"], target_groups=["失业人员"]),
        policy("POLICY-003", region="宁波", topics=["创业补贴"], target_groups=["应届毕业生"]),
    ])
    repository = PolicyRepository(file_path)

    assert [item.policyId for item in repository.filter_by_region("杭州")] == ["POLICY-001", "POLICY-002"]
    assert [item.policyId for item in repository.filter_by_topic("创业补贴")] == ["POLICY-001", "POLICY-003"]
    assert [item.policyId for item in repository.filter_by_target_group("应届毕业生")] == ["POLICY-001", "POLICY-003"]
    assert [item.policyId for item in repository.filter(region="杭州", topic="创业补贴", target_group="应届毕业生")] == ["POLICY-001"]


def test_local_policy_search_tool_adapts_records_to_policy_candidates(tmp_path) -> None:
    file_path = tmp_path / "policies.json"
    write_policies(file_path, [policy("POLICY-001")])
    tool = LocalPolicySearchTool(PolicyRepository(file_path))

    result = asyncio.run(tool.search(
        UserProfile(city="杭州", education="本科", graduationYear=2026, employmentStatus="创业中"),
        "我想了解创业补贴",
    ))

    assert len(result) == 1
    assert result[0].policyId == "POLICY-001"
    assert result[0].isMock is False
    assert result[0].sourceUrl == ""
    assert "不代表真实官方政策" in result[0].summary


def test_local_policy_search_tool_returns_empty_list_when_no_policy_matches(tmp_path) -> None:
    file_path = tmp_path / "policies.json"
    write_policies(file_path, [policy("POLICY-001", region="杭州", topics=["创业补贴"])])
    tool = LocalPolicySearchTool(PolicyRepository(file_path))

    result = asyncio.run(tool.search(
        UserProfile(city="宁波", education="本科", graduationYear=2026, employmentStatus="创业中"),
        "我想了解就业补贴",
    ))

    assert result == []
