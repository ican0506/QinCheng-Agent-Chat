from __future__ import annotations

from app.agent.models import (
    EligibilityResult,
    EligibilityStatus,
    OverallPlan,
    PlanActionType,
    PlanStep,
    PlanStepStatus,
    PolicyCandidate,
    PolicyRelation,
    PolicyRelationType,
)
from app.models.chat import UserProfile
from app.policy.models import ApplicationStatus, ValidityStatus
from app.policy.repository import PolicyRepository


class DeterministicPlanTool:
    """依据确定性资格、时效、窗口和显式关系生成办理步骤。"""

    _field_labels = {
        "graduationDate": "毕业日期",
        "socialInsuranceMonths": "连续社保缴费月数",
        "businessRegistrationMonths": "经营主体登记注册月数",
        "residencyRegistration": "户籍信息",
        "unemploymentStatus": "就业状态",
        "flexibleEmploymentInsurance": "灵活就业参保信息",
        "jobSeekingIntent": "就业创业意愿",
        "hardshipIdentity": "困难毕业生身份",
    }

    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

    async def build_plan(
        self,
        profile: UserProfile,
        policies: list[PolicyCandidate],
        eligibility: list[EligibilityResult],
        relations: list[PolicyRelation],
    ) -> OverallPlan:
        result_by_policy = {item.policyId: item for item in eligibility}
        ordered_policies = self._ordered_policies(policies, relations)
        steps = self._missing_information_steps(ordered_policies, result_by_policy)
        for policy in ordered_policies:
            result = result_by_policy.get(policy.policyId)
            if result is None:
                continue
            steps.extend(self._policy_steps(policy, result))
        steps.sort(key=lambda item: (item.priority, self._first_policy_rank(item, ordered_policies), item.stepId))
        return OverallPlan(
            summary="已依据政策资格、时效、申报窗口和已核验关系生成办理路径。",
            steps=steps,
            notes=["资格判断与政策关系均由确定性规则生成；最终以政府部门最新规定和审核为准。"],
            isMock=False,
        )

    def _missing_information_steps(
        self, policies: list[PolicyCandidate], results: dict[str, EligibilityResult]
    ) -> list[PlanStep]:
        fields: dict[str, list[str]] = {}
        for policy in policies:
            result = results.get(policy.policyId)
            if result is None or result.overallStatus is not EligibilityStatus.UNKNOWN:
                continue
            for field in result.missingFields:
                fields.setdefault(field, []).append(policy.policyId)
        return [
            PlanStep(
                stepId=f"provide-info:{field}",
                title=f"补充{self._field_labels.get(field, field)}",
                description="该信息是继续核验相关政策资格所必需的，请补充后重新判断。",
                policyIds=sorted(policy_ids),
                actionType=PlanActionType.PROVIDE_INFO,
                priority=10,
                status=PlanStepStatus.BLOCKED,
            )
            for field, policy_ids in sorted(fields.items())
        ]

    def _policy_steps(self, policy: PolicyCandidate, result: EligibilityResult) -> list[PlanStep]:
        record = self._repository.get_by_id(policy.policyId)
        if record is None:
            return [self._notice(policy, "缺少本地结构化政策记录，暂不能规划申请步骤。")]
        if record.validityStatus in {ValidityStatus.HISTORICAL, ValidityStatus.EXPIRED}:
            return [self._notice(policy, "该政策记录为历史依据，不能进入当前正常申请路径。")]
        if record.applicationStatus is ApplicationStatus.CLOSED:
            return [PlanStep(
                stepId=f"wait-window:{policy.policyId}", title=f"等待{policy.name}下一轮申报窗口",
                description="资格结论不因窗口关闭而改变；请关注主管部门下一轮申报安排。",
                policyIds=[policy.policyId], actionType=PlanActionType.WAIT_FOR_WINDOW,
                priority=60, status=PlanStepStatus.INFO,
            )]
        if record.applicationStatus is ApplicationStatus.NOT_STARTED:
            return [PlanStep(
                stepId=f"wait-window:{policy.policyId}", title=f"等待{policy.name}开放申报",
                description="当前申报尚未开始，请在开放后按官方安排办理。",
                policyIds=[policy.policyId], actionType=PlanActionType.WAIT_FOR_WINDOW,
                priority=60, status=PlanStepStatus.INFO,
            )]
        if result.overallStatus is EligibilityStatus.FAIL:
            return [self._notice(policy, "当前画像存在明确不满足的资格条件，不进入申请主路径。")]
        if result.overallStatus is EligibilityStatus.UNKNOWN:
            return [PlanStep(
                stepId=f"verify-eligibility:{policy.policyId}", title=f"核验{policy.name}资格",
                description="完成缺失信息补充后，再核验该政策资格。",
                policyIds=[policy.policyId], actionType=PlanActionType.VERIFY_ELIGIBILITY,
                priority=20, status=PlanStepStatus.BLOCKED,
            )]
        if result.overallStatus is EligibilityStatus.MANUAL_REVIEW:
            return self._material_steps(policy, PlanStepStatus.PENDING) + [PlanStep(
                stepId=f"manual-review:{policy.policyId}", title=f"人工核验{policy.name}资格",
                description="准备相关证明材料并向经办机构进行人工核验。",
                policyIds=[policy.policyId], actionType=PlanActionType.MANUAL_REVIEW,
                priority=40, status=PlanStepStatus.BLOCKED,
            )]
        application_note = "申报窗口状态待确认，请在提交前核对官方安排。" if record.applicationStatus is ApplicationStatus.UNKNOWN else ""
        return self._material_steps(policy, PlanStepStatus.PENDING) + [PlanStep(
            stepId=f"apply-policy:{policy.policyId}", title=f"申请{policy.name}",
            description=f"资格条件当前满足。{application_note}", policyIds=[policy.policyId],
            actionType=PlanActionType.APPLY_POLICY, priority=50, status=PlanStepStatus.READY,
        )]

    @staticmethod
    def _material_steps(policy: PolicyCandidate, status: PlanStepStatus) -> list[PlanStep]:
        if not policy.requiredMaterials:
            return []
        return [PlanStep(
            stepId=f"prepare-materials:{policy.policyId}", title=f"准备{policy.name}材料",
            description="按已记录的官方材料要求准备申请材料。", policyIds=[policy.policyId],
            requiredMaterials=policy.requiredMaterials, actionType=PlanActionType.PREPARE_MATERIALS,
            priority=30, status=status,
        )]

    @staticmethod
    def _notice(policy: PolicyCandidate, description: str) -> PlanStep:
        return PlanStep(
            stepId=f"notice:{policy.policyId}", title=f"关注{policy.name}政策状态",
            description=description, policyIds=[policy.policyId], actionType=PlanActionType.NOTICE,
            priority=70, status=PlanStepStatus.INFO,
        )

    @staticmethod
    def _ordered_policies(policies: list[PolicyCandidate], relations: list[PolicyRelation]) -> list[PolicyCandidate]:
        by_id = {policy.policyId: policy for policy in policies}
        edges = {policy_id: set() for policy_id in by_id}
        for relation in relations:
            if relation.relationType is PolicyRelationType.PREREQUISITE and relation.fromPolicyId in by_id and relation.toPolicyId in by_id:
                edges[relation.fromPolicyId].add(relation.toPolicyId)
        incoming = {policy_id: 0 for policy_id in by_id}
        for targets in edges.values():
            for target in targets:
                incoming[target] += 1
        ordered_ids: list[str] = []
        ready = sorted(policy_id for policy_id, count in incoming.items() if count == 0)
        while ready:
            current = ready.pop(0)
            ordered_ids.append(current)
            for target in sorted(edges[current]):
                incoming[target] -= 1
                if incoming[target] == 0:
                    ready.append(target)
                    ready.sort()
        ordered_ids.extend(sorted(set(by_id) - set(ordered_ids)))
        return [by_id[policy_id] for policy_id in ordered_ids]

    @staticmethod
    def _first_policy_rank(step: PlanStep, policies: list[PolicyCandidate]) -> int:
        ranks = {policy.policyId: index for index, policy in enumerate(policies)}
        return min((ranks.get(policy_id, len(ranks)) for policy_id in step.policyIds), default=-1)
