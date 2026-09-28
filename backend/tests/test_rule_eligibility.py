from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from app.agent.models import PolicyCandidate
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository


def policy_data(
    policy_id: str,
    conditions: list[dict],
    *,
    validity_status: str = "ACTIVE",
    application_status: str = "UNKNOWN",
) -> dict:
    return {
        "policyId": policy_id,
        "name": policy_id,
        "region": "苏州市",
        "department": "苏州市人力资源和社会保障局",
        "summary": "测试政策",
        "sourceUrl": "https://www.suzhou.gov.cn/test",
        "targetGroups": ["测试对象"],
        "topics": ["测试"],
        "conditions": conditions,
        "requiredMaterials": [],
        "process": [],
        "isVerified": True,
        "sourceVerified": True,
        "validityStatus": validity_status,
        "lastVerifiedAt": "2026-09-28",
        "applicationStatus": application_status,
    }


def condition(operator: str, value: object, *, field: str = "socialInsuranceMonths", manual: bool = False) -> dict:
    return {
        "conditionId": f"{operator}-{field}",
        "field": field,
        "operator": operator,
        "value": value,
        "description": "测试条件",
        "policyEvidence": "测试依据",
        "evaluationMode": "MANUAL" if manual else "AUTO",
    }


def candidate(policy_id: str) -> PolicyCandidate:
    return PolicyCandidate(
        policyId=policy_id,
        name=policy_id,
        region="苏州市",
        department="苏州市人力资源和社会保障局",
        summary="测试政策",
        effectiveDate="",
        sourceUrl="https://www.suzhou.gov.cn/test",
        matchReason="测试",
        isMock=False,
    )


def tool_for(tmp_path: Path, policies: list[dict]) -> RuleEligibilityTool:
    data_path = tmp_path / "policies.json"
    data_path.write_text(json.dumps(policies, ensure_ascii=False), encoding="utf-8")
    return RuleEligibilityTool(PolicyRepository(data_path), as_of_date=date(2026, 9, 28))


@pytest.mark.parametrize(
    ("operator", "field", "value", "profile_value", "expected"),
    [
        ("eq", "employmentStatus", "创业中", "创业中", "PASS"),
        ("gte", "socialInsuranceMonths", 6, 5, "FAIL"),
        ("lte", "businessRegistrationMonths", 36, 36, "PASS"),
        ("in", "hardshipIdentity", ["低保家庭"], "低保家庭", "PASS"),
        ("not_in", "employmentStatus", ["已就业"], "创业中", "PASS"),
        ("exists", "flexibleEmploymentInsurance", True, True, "PASS"),
    ],
)
def test_each_basic_operator_is_evaluated_independently(
    tmp_path: Path, operator: str, field: str, value: object, profile_value: object, expected: str
) -> None:
    tool = tool_for(tmp_path, [policy_data("operator-policy", [condition(operator, value, field=field)])])
    result = asyncio.run(tool.check(UserProfile.model_validate({field: profile_value}), [candidate("operator-policy")]))[0]

    assert result.conditionResults[0].status == expected


def test_within_years_requires_exact_graduation_date(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("graduation-policy", [condition("within_years", 2, field="graduationYear")])])
    result = asyncio.run(tool.check(UserProfile(graduationYear=2026), [candidate("graduation-policy")]))[0]

    assert result.overallStatus == "UNKNOWN"
    assert result.missingFields == ["graduationDate"]


def test_within_years_passes_with_exact_graduation_date(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("graduation-policy", [condition("within_years", 2, field="graduationYear")])])
    result = asyncio.run(tool.check(UserProfile(graduationDate=date(2025, 6, 30)), [candidate("graduation-policy")]))[0]

    assert result.overallStatus == "PASS"


def test_manual_condition_requires_manual_review_even_when_profile_has_value(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("manual-policy", [condition("eq", True, field="isFirstTimeEntrepreneur", manual=True)])])
    result = asyncio.run(tool.check(UserProfile(isFirstTimeEntrepreneur=True), [candidate("manual-policy")]))[0]

    assert result.overallStatus == "MANUAL_REVIEW"
    assert result.conditionResults[0].status == "MANUAL_REVIEW"


def test_overall_status_uses_fail_manual_unknown_pass_priority(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("priority-policy", [
        condition("gte", 12),
        condition("eq", True, field="isFirstTimeEntrepreneur", manual=True),
        condition("eq", "创业中", field="employmentStatus"),
    ])])
    result = asyncio.run(tool.check(UserProfile(socialInsuranceMonths=6), [candidate("priority-policy")]))[0]

    assert result.overallStatus == "FAIL"


def test_historical_policy_cannot_return_current_pass(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("historical-policy", [condition("eq", "创业中", field="employmentStatus")], validity_status="HISTORICAL")])
    result = asyncio.run(tool.check(UserProfile(employmentStatus="创业中"), [candidate("historical-policy")]))[0]

    assert result.overallStatus == "MANUAL_REVIEW"
    assert any(item.conditionId == "policy-validity" for item in result.conditionResults)


def test_closed_application_window_does_not_turn_eligible_profile_into_fail(tmp_path: Path) -> None:
    tool = tool_for(tmp_path, [policy_data("closed-policy", [condition("eq", "创业中", field="employmentStatus")], application_status="CLOSED")])
    result = asyncio.run(tool.check(UserProfile(employmentStatus="创业中"), [candidate("closed-policy")]))[0]

    assert result.overallStatus == "PASS"
    assert "申报窗口已关闭" in result.summary


@pytest.mark.parametrize(
    ("policy_id", "profile", "expected"),
    [
        ("suzhou-flexible-social-2021", {"graduationDate": "2025-06-30", "residencyRegistration": "本市户籍", "unemploymentStatus": "未就业", "flexibleEmploymentInsurance": True}, "PASS"),
        ("suzhou-startup-one-time-2023", {"graduationDate": "2025-06-30", "socialInsuranceMonths": 5, "businessRegistrationMonths": 12}, "FAIL"),
        ("suzhou-startup-social-2021", {"graduationDate": "2025-06-30", "businessRegistrationMonths": 12}, "UNKNOWN"),
    ],
)
def test_active_suzhou_policies_return_explainable_statuses(
    policy_id: str, profile: dict, expected: str
) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    tool = RuleEligibilityTool(
        PolicyRepository(backend_root / "data" / "policies" / "policies.json"),
        as_of_date=date(2026, 9, 28),
    )
    result = asyncio.run(tool.check(UserProfile.model_validate(profile), [candidate(policy_id)]))[0]

    assert result.overallStatus == expected
    assert result.conditionResults
