from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.chat import MaterialCheckResult, UserProfile
from app.realtime_policy.models import RealtimePolicyHit, RealtimeSearchStatus


class AgentStage(str, Enum):
    PROFILE_COLLECTING = "PROFILE_COLLECTING"
    POLICY_SEARCHING = "POLICY_SEARCHING"
    ELIGIBILITY_CHECKING = "ELIGIBILITY_CHECKING"
    POLICY_COMPARING = "POLICY_COMPARING"
    PLANNING = "PLANNING"
    COMPLETED = "COMPLETED"


class EligibilityStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class PolicyRelationType(str, Enum):
    PREREQUISITE = "PREREQUISITE"
    PARALLEL = "PARALLEL"
    MUTEX = "MUTEX"
    TIME_DEPENDENT = "TIME_DEPENDENT"


class PlanActionType(str, Enum):
    PROVIDE_INFO = "PROVIDE_INFO"
    VERIFY_ELIGIBILITY = "VERIFY_ELIGIBILITY"
    PREPARE_MATERIALS = "PREPARE_MATERIALS"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    APPLY_POLICY = "APPLY_POLICY"
    WAIT_FOR_WINDOW = "WAIT_FOR_WINDOW"
    NOTICE = "NOTICE"


class PlanStepStatus(str, Enum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    READY = "READY"
    INFO = "INFO"


class PolicyCandidate(BaseModel):
    policyId: str
    name: str
    region: str
    department: str
    summary: str
    effectiveDate: str
    expiryDate: str | None = None
    sourceUrl: str
    matchReason: str
    conditions: list[str] = Field(default_factory=list)
    requiredMaterials: list[str] = Field(default_factory=list)
    process: list[str] = Field(default_factory=list)
    isMock: bool = True


class ConditionResult(BaseModel):
    conditionId: str
    description: str
    status: EligibilityStatus
    reason: str
    userEvidence: str | None = None
    policyEvidence: str | None = None


class EligibilityResult(BaseModel):
    policyId: str
    overallStatus: EligibilityStatus
    conditionResults: list[ConditionResult] = Field(default_factory=list)
    missingFields: list[str] = Field(default_factory=list)
    summary: str


class PolicyRelation(BaseModel):
    fromPolicyId: str
    toPolicyId: str
    relationType: PolicyRelationType
    reason: str
    policyEvidence: str | None = None


class PlanStep(BaseModel):
    stepId: str
    title: str
    description: str
    policyIds: list[str] = Field(default_factory=list)
    requiredMaterials: list[str] = Field(default_factory=list)
    actionType: PlanActionType = PlanActionType.NOTICE
    priority: int = 70
    status: PlanStepStatus = PlanStepStatus.INFO


class OverallPlan(BaseModel):
    summary: str
    steps: list[PlanStep] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    isMock: bool = True


class GovernmentAgentState(BaseModel):
    sessionId: str
    userMessage: str
    userProfile: UserProfile
    stage: AgentStage = AgentStage.PROFILE_COLLECTING
    candidatePolicies: list[PolicyCandidate] = Field(default_factory=list)
    eligibilityResults: list[EligibilityResult] = Field(default_factory=list)
    policyRelations: list[PolicyRelation] = Field(default_factory=list)
    overallPlan: OverallPlan | None = None
    materialResults: list[MaterialCheckResult] = Field(default_factory=list)
    materialDeclarations: dict[str, bool] = Field(default_factory=dict)
    needFollowUp: bool = False
    followUpQuestions: list[str] = Field(default_factory=list)
    nextAction: str | None = None
    errors: list[str] = Field(default_factory=list)
    realtimePolicyHits: list[RealtimePolicyHit] = Field(default_factory=list)
    realtimeSearchStatus: RealtimeSearchStatus = RealtimeSearchStatus.NOT_TRIGGERED
