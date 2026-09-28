from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.agent.models import EligibilityResult, EligibilityStatus, PolicyCandidate, PolicyRelation, PolicyRelationType
from app.agent.tools.plan import DeterministicPlanTool
from app.agent.tools.policy_compare import DeterministicPolicyCompareTool
from app.models.chat import UserProfile
from app.policy.relations import PolicyRelationRepository
from app.policy.repository import PolicyRepository


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def repository() -> PolicyRepository:
    return PolicyRepository(BACKEND_ROOT / "data" / "policies" / "policies.json")


def candidate(policy_id: str) -> PolicyCandidate:
    record = repository().get_by_id(policy_id)
    assert record is not None
    return PolicyCandidate(
        policyId=record.policyId, name=record.name, region=record.region,
        department=record.department, summary=record.summary,
        effectiveDate=record.effectiveDate or "", expiryDate=record.expiryDate,
        sourceUrl=record.sourceUrl or "", matchReason="测试", isMock=False,
        conditions=[condition.description for condition in record.conditions],
        requiredMaterials=record.requiredMaterials, process=record.process,
    )


def eligibility(policy_id: str, status: EligibilityStatus, missing: list[str] | None = None) -> EligibilityResult:
    return EligibilityResult(policyId=policy_id, overallStatus=status, missingFields=missing or [], summary="测试资格结果")


def relation_repository(tmp_path: Path, items: list[dict]) -> PolicyRelationRepository:
    path = tmp_path / "policy_relations.json"
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return PolicyRelationRepository(path)


def test_empty_relation_configuration_returns_no_relations(tmp_path: Path) -> None:
    tool = DeterministicPolicyCompareTool(repository(), relation_repository(tmp_path, []))
    policies = [candidate("suzhou-startup-one-time-2023"), candidate("suzhou-startup-social-2021")]

    assert asyncio.run(tool.compare(policies, [eligibility(item.policyId, EligibilityStatus.PASS) for item in policies])) == []


def test_compare_reads_explicit_relation_and_filters_invalid_entries(tmp_path: Path) -> None:
    tool = DeterministicPolicyCompareTool(repository(), relation_repository(tmp_path, [
        {"sourcePolicyId": "suzhou-startup-one-time-2023", "targetPolicyId": "suzhou-startup-social-2021", "relationType": "TIME_DEPENDENT", "reason": "测试时间条件", "policyEvidence": "测试依据"},
        {"sourcePolicyId": "suzhou-startup-one-time-2023", "targetPolicyId": "suzhou-startup-social-2021", "relationType": "TIME_DEPENDENT", "reason": "重复关系", "policyEvidence": "测试依据"},
        {"sourcePolicyId": "suzhou-startup-one-time-2023", "targetPolicyId": "suzhou-startup-one-time-2023", "relationType": "PREREQUISITE", "reason": "自引用", "policyEvidence": "测试依据"},
        {"sourcePolicyId": "unknown", "targetPolicyId": "suzhou-startup-social-2021", "relationType": "MUTEX", "reason": "未知政策", "policyEvidence": "测试依据"},
    ]))
    policies = [candidate("suzhou-startup-one-time-2023"), candidate("suzhou-startup-social-2021")]

    first = asyncio.run(tool.compare(policies, [eligibility(item.policyId, EligibilityStatus.PASS) for item in policies]))
    second = asyncio.run(tool.compare(policies, [eligibility(item.policyId, EligibilityStatus.PASS) for item in policies]))

    assert len(first) == 1
    assert first[0].relationType is PolicyRelationType.TIME_DEPENDENT
    assert first[0].policyEvidence == "测试依据"
    assert first == second


def test_non_candidate_relation_is_not_returned(tmp_path: Path) -> None:
    tool = DeterministicPolicyCompareTool(repository(), relation_repository(tmp_path, [
        {"sourcePolicyId": "suzhou-startup-one-time-2023", "targetPolicyId": "suzhou-startup-social-2021", "relationType": "TIME_DEPENDENT", "reason": "测试", "policyEvidence": "测试依据"},
    ]))

    result = asyncio.run(tool.compare([candidate("suzhou-startup-one-time-2023")], [eligibility("suzhou-startup-one-time-2023", EligibilityStatus.PASS)]))
    assert result == []


def plan_tool() -> DeterministicPlanTool:
    return DeterministicPlanTool(repository())


def test_plan_pass_creates_material_and_apply_steps_in_stable_order() -> None:
    policy = candidate("suzhou-startup-one-time-2023")
    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), [policy], [eligibility(policy.policyId, EligibilityStatus.PASS)], []))

    assert [step.actionType.value for step in plan.steps] == ["PREPARE_MATERIALS", "APPLY_POLICY"]
    assert plan.isMock is False
    assert plan.steps[-1].status.value == "READY"


def test_plan_deduplicates_unknown_fields_and_keeps_pass_policy() -> None:
    pass_policy = candidate("suzhou-startup-one-time-2023")
    unknown_policy = candidate("suzhou-startup-social-2021")
    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), [pass_policy, unknown_policy], [
        eligibility(pass_policy.policyId, EligibilityStatus.PASS),
        eligibility(unknown_policy.policyId, EligibilityStatus.UNKNOWN, ["graduationDate", "socialInsuranceMonths"]),
    ], []))

    assert sum(step.actionType.value == "PROVIDE_INFO" and "毕业日期" in step.title for step in plan.steps) == 1
    assert any(step.actionType.value == "APPLY_POLICY" and pass_policy.policyId in step.policyIds for step in plan.steps)


def test_manual_review_uses_generic_review_and_empty_materials_are_not_invented() -> None:
    policy = candidate("suzhou-employment-internship-2024").model_copy(update={"requiredMaterials": []})
    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), [policy], [eligibility(policy.policyId, EligibilityStatus.MANUAL_REVIEW)], []))

    material_steps = [step for step in plan.steps if step.actionType.value == "PREPARE_MATERIALS"]
    assert material_steps == []
    assert any(step.actionType.value == "MANUAL_REVIEW" for step in plan.steps)
    assert all(step.actionType.value != "APPLY_POLICY" for step in plan.steps)


def test_fail_historical_and_closed_policies_do_not_create_apply_steps() -> None:
    failed = candidate("suzhou-startup-one-time-2023")
    historical_closed = candidate("suzhou-job-seeking-subsidy-2026")
    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), [failed, historical_closed], [
        eligibility(failed.policyId, EligibilityStatus.FAIL),
        eligibility(historical_closed.policyId, EligibilityStatus.PASS),
    ], []))

    assert all(step.actionType.value != "APPLY_POLICY" for step in plan.steps)
    assert any(step.actionType.value in {"WAIT_FOR_WINDOW", "NOTICE"} and historical_closed.policyId in step.policyIds for step in plan.steps)


def test_prerequisite_relation_orders_same_priority_policy_steps_stably() -> None:
    first = candidate("suzhou-startup-one-time-2023")
    second = candidate("suzhou-startup-social-2021")
    relation = PolicyRelation(fromPolicyId=first.policyId, toPolicyId=second.policyId, relationType=PolicyRelationType.PREREQUISITE, reason="测试前置")
    inputs = [second, first]
    results = [eligibility(second.policyId, EligibilityStatus.PASS), eligibility(first.policyId, EligibilityStatus.PASS)]

    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), inputs, results, [relation]))
    apply_order = [step.policyIds[0] for step in plan.steps if step.actionType.value == "APPLY_POLICY"]

    assert apply_order == [first.policyId, second.policyId]


def test_flexible_employment_pass_creates_apply_path() -> None:
    policy = candidate("suzhou-flexible-social-2021")
    plan = asyncio.run(plan_tool().build_plan(UserProfile(city="苏州市"), [policy], [eligibility(policy.policyId, EligibilityStatus.PASS)], []))

    assert any(step.actionType.value == "APPLY_POLICY" for step in plan.steps)
