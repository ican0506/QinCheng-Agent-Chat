import type { ChatData, EligibilityResult, UserProfile } from "../types/chat.js";

export function getEligibilityByPolicyId(
  data: ChatData | undefined,
  policyId: string,
): EligibilityResult | undefined {
  return data?.eligibility.find((item) => item.policyId === policyId);
}

export interface ProfileDisplayItem {
  key: string;
  label: string;
  value: string;
}

export function profileDisplayItems(profile: UserProfile): ProfileDisplayItem[] {
  const fields: Array<[string, string, string | number | boolean | null | undefined]> = [
    ["city", "所在地区", profile.city],
    ["education", "学历", profile.education],
    ["graduationYear", "毕业年份", profile.graduationYear],
    ["employmentStatus", "当前状态", profile.employmentStatus],
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
