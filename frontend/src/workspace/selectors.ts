import type { ChatData, EligibilityResult, UserProfile } from "../types/chat.js";

export function getEligibilityByPolicyId(
  data: ChatData | undefined,
  policyId: string,
): EligibilityResult | undefined {
  return data?.eligibility.find((item) => item.policyId === policyId);
}

export function isPolicyMaterialReferenceOnly(data: ChatData | undefined, policyId: string): boolean {
  const eligibility = getEligibilityByPolicyId(data, policyId);
  return Boolean(
    eligibility?.conditionResults.some((item) => item.conditionId === "policy-validity")
    || eligibility?.summary.includes("申报窗口已关闭"),
  );
}

export interface ProfileDisplayItem {
  key: string;
  label: string;
  value: string;
}

const baseProfileFields: Array<[keyof UserProfile, string]> = [
  ["city", "所在地区"],
  ["education", "学历"],
  ["graduationYear", "毕业年份"],
  ["employmentStatus", "当前就业状态"],
];

/** 与后端 ProfileNode 使用相同的基础画像门槛，避免 UI 展示过期追问。 */
export function profileMissingFields(profile: UserProfile): string[] {
  return baseProfileFields
    .filter(([key]) => profile[key] === null || profile[key] === undefined || profile[key] === "")
    .map(([, label]) => label);
}

export function profileDisplayItems(profile: UserProfile): ProfileDisplayItem[] {
  const fields: Array<[string, string, string | number | boolean | null | undefined]> = [
    ["city", "所在地区", profile.city],
    ["education", "学历", profile.education],
    ["graduationYear", "毕业年份", profile.graduationYear],
    ["graduationMonth", "毕业月份", profile.graduationMonth],
    ["employmentStatus", "当前状态", profile.employmentStatus],
    ["residencyRegistration", "户籍", profile.residencyRegistration],
    ["flexibleEmploymentInsurance", "灵活就业参保缴费", profile.flexibleEmploymentInsurance === null || profile.flexibleEmploymentInsurance === undefined ? null : profile.flexibleEmploymentInsurance ? "是" : "否"],
    ["entrepreneurshipIntent", "创业状态", profile.entrepreneurshipIntent === null || profile.entrepreneurshipIntent === undefined ? null : profile.entrepreneurshipIntent ? "准备/正在创业" : "不创业"],
    ["isFirstTimeEntrepreneur", "是否首次创业", profile.isFirstTimeEntrepreneur === null || profile.isFirstTimeEntrepreneur === undefined ? null : profile.isFirstTimeEntrepreneur ? "是" : "否"],
    ["enterpriseRegisterDate", "企业注册日期", profile.enterpriseRegisterDate],
    ["socialInsuranceMonths", "社保缴费月数", profile.socialInsuranceMonths],
    ["housingStatus", "住房情况", profile.housingStatus],
  ];
  return fields
    .filter(([, , value]) => value !== null && value !== undefined && value !== "")
    .map(([key, label, value]) => ({ key, label, value: String(value) }));
}

export function safeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}
