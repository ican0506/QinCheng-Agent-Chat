import type { MaterialResult, MaterialStatus } from "../types/chat.js";

export const materialStatusLabels: Record<MaterialStatus, string> = {
  READY: "已准备", MISSING: "未准备", UNKNOWN: "待确认", MANUAL_REVIEW: "需人工核验",
};

export function materialDeclarationMessage(material: MaterialResult, prepared: boolean): string {
  return prepared ? `我已经准备好${material.materialName}` : `我还没有准备${material.materialName}`;
}

/** 只决定展示操作，不修改后端材料状态。历史参考始终只读。 */
export function materialActions(status: MaterialStatus, referenceOnly: boolean): boolean[] {
  if (referenceOnly) return [];
  if (status === "UNKNOWN") return [true, false];
  if (status === "MISSING") return [true];
  return [];
}
