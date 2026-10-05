/** 展示映射仅翻译已返回信息，不推断政策状态或资格。 */
const fieldLabels: Record<string, string> = {
  city: "所在地区", education: "学历", graduationYear: "毕业年份",
  graduationDate: "毕业日期", employmentStatus: "就业状态",
  socialInsuranceMonths: "社保连续缴纳月数", businessRegistrationMonths: "经营主体登记注册时长",
  residencyRegistration: "户籍情况", flexibleEmploymentInsurance: "是否已按灵活就业身份参保缴费",
  unemploymentStatus: "失业情况", jobSeekingIntent: "求职意愿", entrepreneurshipIntent: "创业意愿",
  hardshipIdentity: "困难毕业生身份", isFirstTimeEntrepreneur: "是否首次创业",
  enterpriseRegisterDate: "企业注册日期", housingStatus: "住房情况",
};
const stateLabels: Record<string, string> = {
  ACTIVE: "当前有效", HISTORICAL: "历史政策", EXPIRED: "已失效",
  CLOSED: "申报已结束", OPEN: "申报中", NOT_STARTED: "申报尚未开始",
  UNKNOWN: "状态待核实", PASS: "基本符合", FAIL: "暂不符合", MANUAL_REVIEW: "需要人工核验",
  validityStatus: "政策有效性", applicationStatus: "申报状态", lastVerifiedAt: "最后核验日期",
};

export function missingFieldLabel(field: string): string {
  return fieldLabels[field] ?? "需补充相关信息";
}

export function formatWorkspaceText(text: string): string {
  return text
    .replace(/(?:政策\s*ID|policyId)\s*[：:]\s*[\w-]+\s*/gi, "")
    .replace(/(?:Dify\s*)?知识库命中原文片段/g, "匹配到政策原文")
    .replace(/RAG\s*命中/g, "匹配")
    .replace(/[（(]相关度\s*[\d.]+[）)]/g, "")
    .replace(/(?:ragScore|RAG\s*相关度)\s*[：:]?\s*[\d.]+/gi, "")
    .replace(/缺少字段[：:]\s*([A-Za-z][\w]*)/g, (_match, field: string) => `缺少字段：${missingFieldLabel(field)}`)
    .replace(/\b[A-Za-z][A-Za-z_]*\b/g, (word) => fieldLabels[word] ?? stateLabels[word] ?? (word === "RAG" ? "政策原文检索" : word))
    .trim();
}
