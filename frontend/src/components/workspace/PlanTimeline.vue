<script setup lang="ts">
import { ClipboardList } from "@lucide/vue";
import type { OverallPlan, PlanActionType, PlanStepStatus } from "../../types/chat";
defineProps<{ plan: OverallPlan | null }>();
const actionLabels: Record<PlanActionType, string> = { PROVIDE_INFO: "补充信息", VERIFY_ELIGIBILITY: "核验资格", PREPARE_MATERIALS: "准备材料", MANUAL_REVIEW: "人工核验", APPLY_POLICY: "申请办理", WAIT_FOR_WINDOW: "等待申报窗口", NOTICE: "提示" };
const statusLabels: Record<PlanStepStatus, string> = { PENDING: "待处理", BLOCKED: "等待补充", READY: "可进行", INFO: "提示" };
</script>

<template>
  <section class="workspace-section">
    <div class="action-title"><ClipboardList :size="18" /><strong>办理计划</strong></div>
    <p v-if="!plan" class="workspace-muted">暂无办理计划。</p>
    <template v-else>
      <p class="plan-summary">{{ plan.summary }}</p>
      <ol v-if="plan.steps.length" class="plan-timeline"><li v-for="step in plan.steps" :key="step.stepId"><div><strong>{{ step.title }}</strong><span>{{ actionLabels[step.actionType] }} · {{ statusLabels[step.status] }}</span></div><p>{{ step.description }}</p><ul v-if="step.requiredMaterials.length"><li v-for="material in step.requiredMaterials" :key="material">{{ material }}</li></ul></li></ol>
      <p v-else class="workspace-muted">暂无具体办理步骤。</p>
      <ul v-if="plan.notes.length" class="plan-notes"><li v-for="note in plan.notes" :key="note">{{ note }}</li></ul>
    </template>
  </section>
</template>
