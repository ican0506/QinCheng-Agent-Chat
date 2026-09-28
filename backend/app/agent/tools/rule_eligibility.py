from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.agent.models import (
    ConditionResult,
    EligibilityResult,
    EligibilityStatus,
    PolicyCandidate,
)
from app.models.chat import UserProfile
from app.policy.models import (
    ApplicationStatus,
    ConditionOperator,
    EvaluationMode,
    PolicyCondition,
    PolicyRecord,
    ValidityStatus,
)
from app.policy.repository import PolicyRepository


@dataclass(frozen=True)
class _Evaluation:
    status: EligibilityStatus
    reason: str
    missing_field: str | None = None
    user_evidence: str | None = None


class RuleEligibilityTool:
    """基于本地 PolicyRecord 的确定性资格规则工具。"""

    def __init__(self, repository: PolicyRepository, *, as_of_date: date | None = None) -> None:
        self._repository = repository
        self._as_of_date = as_of_date or date.today()
        self._evaluators: dict[ConditionOperator, Callable[[PolicyCondition, UserProfile], _Evaluation]] = {
            ConditionOperator.EQ: self._evaluate_eq,
            ConditionOperator.GTE: self._evaluate_gte,
            ConditionOperator.LTE: self._evaluate_lte,
            ConditionOperator.IN: self._evaluate_in,
            ConditionOperator.NOT_IN: self._evaluate_not_in,
            ConditionOperator.EXISTS: self._evaluate_exists,
            ConditionOperator.WITHIN_YEARS: self._evaluate_within_years,
        }

    async def check(
        self, profile: UserProfile, policies: list[PolicyCandidate]
    ) -> list[EligibilityResult]:
        return [self._check_policy(profile, policy) for policy in policies]

    def _check_policy(self, profile: UserProfile, candidate: PolicyCandidate) -> EligibilityResult:
        record = self._repository.get_by_id(candidate.policyId)
        if record is None:
            return EligibilityResult(
                policyId=candidate.policyId,
                overallStatus=EligibilityStatus.MANUAL_REVIEW,
                conditionResults=[ConditionResult(
                    conditionId="policy-record", description="政策结构化记录", status=EligibilityStatus.MANUAL_REVIEW,
                    reason="本地政策库中未找到该政策的结构化规则，不能自动判断。",
                )],
                summary="缺少可用的结构化政策规则，需要人工核验。",
            )

        condition_results: list[ConditionResult] = []
        missing_fields: list[str] = []
        validity_result = self._validity_result(record)
        if validity_result is not None:
            condition_results.append(validity_result)

        for condition in record.conditions:
            result = self._evaluate_condition(condition, profile)
            condition_results.append(result)
            if result.status is EligibilityStatus.UNKNOWN and result.reason.startswith("缺少字段："):
                missing_fields.append(result.reason.removeprefix("缺少字段："))

        overall_status = self._overall_status(condition_results)
        summary = self._summary(record, overall_status)
        return EligibilityResult(
            policyId=record.policyId,
            overallStatus=overall_status,
            conditionResults=condition_results,
            missingFields=list(dict.fromkeys(missing_fields)),
            summary=summary,
        )

    def _evaluate_condition(self, condition: PolicyCondition, profile: UserProfile) -> ConditionResult:
        if condition.evaluationMode is EvaluationMode.MANUAL:
            evaluation = _Evaluation(
                EligibilityStatus.MANUAL_REVIEW,
                "该条件需要材料或经办机构认定，不能依据当前用户画像自动判断。",
            )
        else:
            evaluation = self._evaluators[condition.operator](condition, profile)
        return ConditionResult(
            conditionId=condition.conditionId,
            description=condition.description,
            status=evaluation.status,
            reason=evaluation.reason,
            userEvidence=evaluation.user_evidence,
            policyEvidence=condition.policyEvidence,
        )

    def _profile_value(self, profile: UserProfile, field: str) -> Any:
        return getattr(profile, field, None)

    def _missing(self, field: str) -> _Evaluation:
        return _Evaluation(EligibilityStatus.UNKNOWN, f"缺少字段：{field}", missing_field=field)

    def _automatic_comparison(
        self, condition: PolicyCondition, profile: UserProfile, predicate: Callable[[Any, Any], bool]
    ) -> _Evaluation:
        value = self._profile_value(profile, condition.field)
        if value is None:
            return self._missing(condition.field)
        try:
            matched = predicate(value, condition.value)
        except TypeError:
            return _Evaluation(EligibilityStatus.MANUAL_REVIEW, "用户字段与政策条件的数据类型无法可靠比较。")
        status = EligibilityStatus.PASS if matched else EligibilityStatus.FAIL
        reason = "用户信息满足该条件。" if matched else "用户信息不满足该条件。"
        return _Evaluation(status, reason, user_evidence=str(value))

    def _evaluate_eq(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        return self._automatic_comparison(condition, profile, lambda actual, expected: actual == expected)

    def _evaluate_gte(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        return self._automatic_comparison(condition, profile, lambda actual, expected: actual >= expected)

    def _evaluate_lte(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        return self._automatic_comparison(condition, profile, lambda actual, expected: actual <= expected)

    def _evaluate_in(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        return self._automatic_comparison(condition, profile, lambda actual, expected: actual in expected)

    def _evaluate_not_in(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        return self._automatic_comparison(condition, profile, lambda actual, expected: actual not in expected)

    def _evaluate_exists(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        value = self._profile_value(profile, condition.field)
        if value is None:
            return self._missing(condition.field)
        expected = condition.value
        matched = value is not None if expected is None else value == expected
        status = EligibilityStatus.PASS if matched else EligibilityStatus.FAIL
        reason = "用户信息满足该条件。" if matched else "用户信息不满足该条件。"
        return _Evaluation(status, reason, user_evidence=str(value))

    def _evaluate_within_years(self, condition: PolicyCondition, profile: UserProfile) -> _Evaluation:
        if condition.field == "graduationYear":
            graduation_date = profile.graduationDate
            if graduation_date is None:
                return self._missing("graduationDate")
            try:
                deadline = graduation_date.replace(year=graduation_date.year + int(condition.value))
            except ValueError:
                deadline = graduation_date.replace(month=2, day=28, year=graduation_date.year + int(condition.value))
            matched = self._as_of_date <= deadline
            status = EligibilityStatus.PASS if matched else EligibilityStatus.FAIL
            reason = "毕业日期在政策规定年限内。" if matched else "毕业日期已超出政策规定年限。"
            return _Evaluation(status, reason, user_evidence=graduation_date.isoformat())
        return _Evaluation(
            EligibilityStatus.MANUAL_REVIEW,
            "当前仅支持基于 graduationDate 的精确年限判断。",
        )

    def _validity_result(self, record: PolicyRecord) -> ConditionResult | None:
        if record.validityStatus is ValidityStatus.ACTIVE:
            return None
        if record.validityStatus in {ValidityStatus.HISTORICAL, ValidityStatus.EXPIRED}:
            reason = "该记录为历史政策或历史申报通知，不能作为当前申请依据。"
        else:
            reason = "该政策当前有效性尚未确认，不能作为当前申请依据。"
        return ConditionResult(
            conditionId="policy-validity",
            description="政策时效性",
            status=EligibilityStatus.MANUAL_REVIEW,
            reason=reason,
        )

    @staticmethod
    def _overall_status(results: list[ConditionResult]) -> EligibilityStatus:
        statuses = {result.status for result in results}
        if EligibilityStatus.FAIL in statuses:
            return EligibilityStatus.FAIL
        if EligibilityStatus.MANUAL_REVIEW in statuses:
            return EligibilityStatus.MANUAL_REVIEW
        if EligibilityStatus.UNKNOWN in statuses:
            return EligibilityStatus.UNKNOWN
        return EligibilityStatus.PASS

    @staticmethod
    def _summary(record: PolicyRecord, status: EligibilityStatus) -> str:
        summary = {
            EligibilityStatus.PASS: "结构化资格条件均满足。",
            EligibilityStatus.FAIL: "存在明确不满足的资格条件。",
            EligibilityStatus.UNKNOWN: "缺少判断资格所需的用户信息。",
            EligibilityStatus.MANUAL_REVIEW: "需要人工复核材料或政策时效后才能确认。",
        }[status]
        if record.applicationStatus is ApplicationStatus.CLOSED:
            return f"{summary} 资格条件与申报窗口独立：当前申报窗口已关闭。"
        return summary
