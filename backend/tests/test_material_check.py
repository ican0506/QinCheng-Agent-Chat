from __future__ import annotations

import asyncio
from pathlib import Path

from app.agent.models import EligibilityResult, EligibilityStatus, PolicyCandidate
from app.agent.tools.material_check import MaterialCheckTool
from app.stores.session_store import InMemorySessionStore
from app.policy.repository import PolicyRepository


ROOT = Path(__file__).resolve().parents[1]


def repository() -> PolicyRepository:
    return PolicyRepository(ROOT / "data" / "policies" / "policies.json")


def candidate(policy_id: str) -> PolicyCandidate:
    record = repository().get_by_id(policy_id)
    assert record is not None
    return PolicyCandidate(policyId=record.policyId, name=record.name, region=record.region, department=record.department, summary=record.summary, effectiveDate=record.effectiveDate or "", expiryDate=record.expiryDate, sourceUrl=record.sourceUrl or "", matchReason="测试", conditions=[], requiredMaterials=record.requiredMaterials, process=record.process, isMock=False)


def check(message: str, policies: list[PolicyCandidate], declarations: dict[str, bool] | None = None):
    return asyncio.run(MaterialCheckTool(repository()).check(message, policies, declarations or {}))


def test_concrete_materials_default_to_unknown_and_declarations_update_status() -> None:
    policy = candidate("suzhou-startup-one-time-2023")
    results, declarations = check("我想申请", [policy])
    assert len(results) == 4
    assert {item.status.value for item in results} == {"UNKNOWN"}
    ready, _ = check("营业执照我准备好了", [policy], declarations)
    assert next(item for item in ready if "营业执照" in item.materialName).status.value == "READY"
    missing, _ = check("没有毕业证", [policy], declarations)
    assert next(item for item in missing if "毕业证" in item.materialName).status.value == "MISSING"


def test_material_declaration_with_brackets_and_alternate_ready_wording_updates_status() -> None:
    policy = candidate("suzhou-startup-social-2021")

    results, declarations = check("我已经准备好《苏州市创业社会保险补贴申请表》", [policy])

    application = next(item for item in results if item.materialName == "《苏州市创业社会保险补贴申请表》")
    assert application.status.value == "READY"
    assert declarations[application.materialId] is True


def test_manual_review_placeholder_and_policy_scoping() -> None:
    policy = candidate("suzhou-job-seeking-subsidy-2026")
    results, _ = check("我想申领", [policy])
    assert any(item.status.value == "MANUAL_REVIEW" for item in results)
    assert all(item.policyId == policy.policyId for item in results)
    vague = candidate("suzhou-flexible-social-2021")
    assert check("我想申请", [vague])[0] == []


def test_same_material_for_two_policies_keeps_distinct_policy_ids() -> None:
    first = candidate("suzhou-startup-one-time-2023")
    second = candidate("suzhou-startup-social-2021")
    results, _ = check("营业执照有了", [first, second])
    licenses = [item for item in results if "营业执照" in item.materialName]
    assert len(licenses) == 2
    assert len({item.materialId for item in licenses}) == 2
    assert {item.policyId for item in licenses} == {first.policyId, second.policyId}


def test_material_results_do_not_change_eligibility() -> None:
    eligibility = EligibilityResult(policyId="policy", overallStatus=EligibilityStatus.PASS, summary="原结论")
    assert eligibility.overallStatus is EligibilityStatus.PASS


def test_session_material_declarations_are_isolated() -> None:
    async def scenario() -> None:
        store = InMemorySessionStore()
        await store.set_material_declarations("session-a", "user", {"a:material": True})
        assert await store.get_material_declarations("session-a", "user") == {"a:material": True}
        assert await store.get_material_declarations("session-b", "user") == {}
    asyncio.run(scenario())
