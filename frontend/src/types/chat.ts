export interface ProfileField {
  key: string;
  value: string;
  source: "user_stated" | "document_extracted" | "system_inferred";
}

export interface UserProfile {
  userId?: string | null;
  city?: string | null;
  education?: "本科" | "硕士" | "专科" | "其他" | null;
  graduationYear?: number | null;
  graduationMonth?: number | null;
  employmentStatus?: "待就业" | "已就业" | "创业中" | null;
  isFirstTimeEntrepreneur?: boolean | null;
  enterpriseRegisterDate?: string | null;
  socialInsuranceMonths?: number | null;
  residencyRegistration?: string | null;
  flexibleEmploymentInsurance?: boolean | null;
  entrepreneurshipIntent?: boolean | null;
  housingStatus?: "租房" | "自有" | "其他" | null;
  fields?: ProfileField[];
}

export interface ChatRequest {
  sessionId: string;
  userId: string;
  message: string;
  userProfile: UserProfile;
  webSearch?: boolean;
}

/** 联网搜索引用来源（Agent 调用 search_web 后返回）。 */
export interface WebSource {
  title: string;
  url: string;
}

export interface ChatData {
  sessionId: string;
  replyText: string;
  needFollowUp: boolean;
  followUpQuestions: string[];
  userProfile: UserProfile;
  policies: PolicyCandidate[];
  eligibility: EligibilityResult[];
  plan: OverallPlan | null;
  materialResults: MaterialResult[];
  sources?: WebSource[];
  suggestedActions?: SuggestedAction[];
  applicationGuide?: boolean;
}

export interface SuggestedAction {
  label: string;
  prompt: string;
}

export type EligibilityStatus = "PASS" | "FAIL" | "UNKNOWN" | "MANUAL_REVIEW";

export interface PolicyCandidate {
  policyId: string;
  name: string;
  region: string;
  department: string;
  summary: string;
  effectiveDate: string;
  expiryDate: string | null;
  sourceUrl: string;
  matchReason: string;
  conditions: string[];
  requiredMaterials: string[];
  process: string[];
  isMock: boolean;
}

export interface ConditionResult {
  conditionId: string;
  description: string;
  status: EligibilityStatus;
  reason: string;
  userEvidence: string | null;
  policyEvidence: string | null;
}

export interface EligibilityResult {
  policyId: string;
  overallStatus: EligibilityStatus;
  conditionResults: ConditionResult[];
  missingFields: string[];
  summary: string;
}

export type PlanActionType =
  | "PROVIDE_INFO"
  | "VERIFY_ELIGIBILITY"
  | "PREPARE_MATERIALS"
  | "MANUAL_REVIEW"
  | "APPLY_POLICY"
  | "WAIT_FOR_WINDOW"
  | "NOTICE";

export type PlanStepStatus = "PENDING" | "BLOCKED" | "READY" | "INFO";

export interface PlanStep {
  stepId: string;
  title: string;
  description: string;
  policyIds: string[];
  requiredMaterials: string[];
  actionType: PlanActionType;
  priority: number;
  status: PlanStepStatus;
}

export interface OverallPlan {
  summary: string;
  steps: PlanStep[];
  notes: string[];
  isMock: boolean;
}

/** 后端当前仅声明材料结果为对象数组，具体字段尚未公开。 */
export type MaterialStatus = "READY" | "MISSING" | "UNKNOWN" | "MANUAL_REVIEW";

export interface MaterialResult {
  materialId: string;
  policyId: string;
  materialName: string;
  description: string | null;
  status: MaterialStatus;
  reason: string;
  source: "POLICY";
  userProvided: boolean;
  needsManualReview: boolean;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  traceId: string;
  data: T | null;
}
