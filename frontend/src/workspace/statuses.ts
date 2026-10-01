import type { EligibilityStatus, MaterialStatus } from "../types/chat.js";
export const eligibilityStatusLabels: Record<EligibilityStatus, string> = { PASS: "基本符合", FAIL: "暂不符合", UNKNOWN: "信息不足，暂无法判断", MANUAL_REVIEW: "需要人工核验" };
export const materialStatusLabels: Record<MaterialStatus, string> = { READY: "已准备", MISSING: "未准备", UNKNOWN: "待确认", MANUAL_REVIEW: "需人工核验" };
