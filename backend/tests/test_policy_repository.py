from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

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


def test_project_policies_json_loads_verified_records() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )

    records = repository.filter()
    assert len(records) >= 5
    assert all(record.isVerified for record in records)


def test_verified_project_policies_have_official_sources_unique_ids_and_raw_files() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    repository = PolicyRepository(backend_root / "data" / "policies" / "policies.json")
    records = repository.filter()

    assert len({record.policyId for record in records}) == len(records)
    for record in records:
        assert record.isVerified is True
        assert record.sourceVerified is True
        assert record.name.strip()
        assert record.department.strip()
        assert record.region == "苏州市"
        assert record.sourceUrl
        source = urlparse(record.sourceUrl)
        assert source.scheme == "https"
        assert source.hostname in {"hrss.suzhou.gov.cn", "www.suzhou.gov.cn"}
        assert "placeholder" not in record.sourceUrl.lower()
        assert (backend_root / "data" / "policies" / "raw" / f"{record.policyId}.md").is_file()


def test_active_policies_have_current_source_and_verification_date() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )

    active_records = [item for item in repository.filter() if item.validityStatus == "ACTIVE"]
    assert active_records
    assert all(item.sourceVerified and item.sourceUrl and item.lastVerifiedAt for item in active_records)


def test_historical_annual_notice_keeps_closed_window_separate_from_expiry() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )
    annual_policy = repository.get_by_id("suzhou-job-seeking-subsidy-2026")

    assert annual_policy is not None
    assert annual_policy.validityStatus == "HISTORICAL"
    assert annual_policy.applicationStatus == "CLOSED"
    assert annual_policy.applicationEndDate is not None
    assert annual_policy.applicableCohorts == ["2026届"]
    assert any(
        condition.field == "graduationYear" and condition.operator.value == "eq"
        for condition in annual_policy.conditions
    )


def test_application_window_metadata_has_consistent_dates_and_cohorts() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )

    for record in repository.filter():
        assert all(cohort.strip() for cohort in record.applicableCohorts)
        if record.applicationStatus == "CLOSED":
            assert record.applicationEndDate is not None
        if record.applicationStatus == "OPEN":
            assert record.applicationStartDate is not None
            assert record.applicationEndDate is not None
            assert record.applicationStartDate <= record.lastVerifiedAt <= record.applicationEndDate


def test_verified_project_policy_conditions_have_unique_ids_and_allowed_operators() -> None:
    repository = PolicyRepository(
        Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json"
    )

    for record in repository.filter():
        condition_ids = [condition.conditionId for condition in record.conditions]
        assert len(condition_ids) == len(set(condition_ids))
        assert all(condition.operator.value in {
            "eq", "gte", "lte", "in", "not_in", "exists", "within_years"
        } for condition in record.conditions)


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


def test_local_policy_search_tool_finds_verified_suzhou_policy() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    tool = LocalPolicySearchTool(
        PolicyRepository(backend_root / "data" / "policies" / "policies.json")
    )

    result = asyncio.run(tool.search(
        UserProfile(city="苏州市", education="本科", graduationYear=2026, employmentStatus="创业中"),
        "我想了解创业补贴",
    ))

    assert result
    assert all(item.region == "苏州市" and item.isMock is False for item in result)
