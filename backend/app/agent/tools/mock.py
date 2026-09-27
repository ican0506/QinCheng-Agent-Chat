from __future__ import annotations

from app.agent.models import (
    ConditionResult,
    EligibilityResult,
    EligibilityStatus,
    OverallPlan,
    PlanStep,
    PolicyCandidate,
    PolicyRelation,
    PolicyRelationType,
)
from app.models.chat import UserProfile


class MockPolicySearchTool:
    def __init__(self) -> None:
        self.call_count = 0

    async def search(self, profile: UserProfile, message: str) -> list[PolicyCandidate]:
        self.call_count += 1
        city = profile.city or "示例地区"
        return [
            PolicyCandidate(
                policyId="DEMO-STARTUP-001", name="毕业生创业补贴（Demo）", region=city,
                department="Demo 人社服务部门", summary="仅用于 Workflow Agent 演示的创业补贴政策。",
                effectiveDate="2026-01-01", expiryDate=None, sourceUrl="https://example.invalid/demo/startup",
                matchReason="用户为应届毕业生且当前处于创业中。", conditions=["应届毕业生", "处于创业状态"],
                requiredMaterials=["身份证明", "毕业证明", "创业主体信息"], process=["准备材料", "提交申请", "等待审核"],
            ),
            PolicyCandidate(
                policyId="DEMO-RENT-002", name="创业场地补贴（Demo）", region=city,
                department="Demo 人社服务部门", summary="仅用于 Workflow Agent 演示的场地补贴政策。",
                effectiveDate="2026-01-01", expiryDate=None, sourceUrl="https://example.invalid/demo/rent",
                matchReason="用户可能需要创业场地支持，但场地情况尚未提供。", conditions=["应届毕业生", "具备符合条件的创业场地"],
                requiredMaterials=["毕业证明", "场地租赁证明"], process=["补充场地信息", "提交申请", "等待审核"],
            ),
            PolicyCandidate(
                policyId="DEMO-SOCIAL-003", name="创业社保补贴（Demo）", region=city,
                department="Demo 人社服务部门", summary="仅用于 Workflow Agent 演示的社保补贴政策。",
                effectiveDate="2026-01-01", expiryDate=None, sourceUrl="https://example.invalid/demo/social",
                matchReason="用户创业相关诉求与社保支持主题相关。", conditions=["应届毕业生", "社保缴费满 6 个月"],
                requiredMaterials=["毕业证明", "社保缴费记录"], process=["核验缴费记录", "提交申请", "等待审核"],
            ),
        ]


class MockEligibilityTool:
    async def check(self, profile: UserProfile, policies: list[PolicyCandidate]) -> list[EligibilityResult]:
        results: list[EligibilityResult] = []
        for policy in policies:
            if policy.policyId == "DEMO-STARTUP-001":
                results.append(EligibilityResult(policyId=policy.policyId, overallStatus=EligibilityStatus.PASS, summary="Demo 判断：基本画像满足创业补贴演示条件。", conditionResults=[ConditionResult(conditionId="graduate", description="应届毕业生", status=EligibilityStatus.PASS, reason="已提供毕业年份与学历。", userEvidence=str(profile.graduationYear), policyEvidence="Demo 条件：应届毕业生"), ConditionResult(conditionId="startup", description="处于创业状态", status=EligibilityStatus.PASS, reason="用户画像标记为创业中。", userEvidence=profile.employmentStatus, policyEvidence="Demo 条件：创业中")]))
            elif policy.policyId == "DEMO-RENT-002":
                results.append(EligibilityResult(policyId=policy.policyId, overallStatus=EligibilityStatus.UNKNOWN, missingFields=["housingStatus"], summary="Demo 判断：缺少创业场地信息，需人工或补充信息确认。", conditionResults=[ConditionResult(conditionId="venue", description="具备符合条件的创业场地", status=EligibilityStatus.UNKNOWN, reason="未提供场地或租赁情况。", policyEvidence="Demo 条件：符合条件的创业场地")]))
            else:
                results.append(EligibilityResult(policyId=policy.policyId, overallStatus=EligibilityStatus.FAIL, summary="Demo 判断：当前画像不满足社保缴费时长演示条件。", conditionResults=[ConditionResult(conditionId="social-insurance", description="社保缴费满 6 个月", status=EligibilityStatus.FAIL, reason="未提供满足要求的社保缴费月数。", userEvidence=str(profile.socialInsuranceMonths) if profile.socialInsuranceMonths is not None else "未提供", policyEvidence="Demo 条件：社保缴费满 6 个月")]))
        return results


class MockPolicyCompareTool:
    async def compare(self, policies: list[PolicyCandidate], eligibility: list[EligibilityResult]) -> list[PolicyRelation]:
        return [
            PolicyRelation(fromPolicyId="DEMO-STARTUP-001", toPolicyId="DEMO-RENT-002", relationType=PolicyRelationType.PARALLEL, reason="Demo：两项支持可并行准备。"),
            PolicyRelation(fromPolicyId="DEMO-STARTUP-001", toPolicyId="DEMO-SOCIAL-003", relationType=PolicyRelationType.TIME_DEPENDENT, reason="Demo：社保缴费条件需在后续满足后再判断。"),
        ]


class MockPlanTool:
    async def build_plan(self, policies: list[PolicyCandidate], eligibility: list[EligibilityResult], relations: list[PolicyRelation]) -> OverallPlan:
        return OverallPlan(summary="这是基于 Mock 政策和固定规则生成的演示办理计划，不代表真实政策结论。", steps=[PlanStep(stepId="prepare-startup", title="优先准备创业补贴申请", description="Demo 判断为 PASS，可先整理创业补贴的申请材料。", policyIds=["DEMO-STARTUP-001"], requiredMaterials=["身份证明", "毕业证明", "创业主体信息"]), PlanStep(stepId="confirm-venue", title="补充创业场地信息", description="场地补贴为 UNKNOWN，需要补充租赁或场地证明。", policyIds=["DEMO-RENT-002"], requiredMaterials=["场地租赁证明"]), PlanStep(stepId="review-social", title="暂不申请社保补贴", description="社保补贴 Demo 判断为 FAIL，满足缴费时长后再核验。", policyIds=["DEMO-SOCIAL-003"], requiredMaterials=["社保缴费记录"])], notes=["所有政策均为 Demo 数据，请以当地官方发布为准。"])
