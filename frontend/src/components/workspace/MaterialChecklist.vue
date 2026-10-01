<script setup lang="ts">
import { ClipboardCheck } from "@lucide/vue";
import { materialStatusLabels, materialActions } from "../../workspace/materials";
import { formatWorkspaceText } from "../../workspace/display";
import type { MaterialResult } from "../../types/chat";

const props = defineProps<{ results: MaterialResult[]; policyNames: Record<string, string>; referencePolicyIds: ReadonlySet<string>; busy: boolean }>();
const emit = defineEmits<{ declare: [material: MaterialResult, prepared: boolean] }>();

function isReferenceOnly(material: MaterialResult): boolean {
  return props.referencePolicyIds.has(material.policyId);
}
</script>

<template>
  <section class="workspace-section">
    <div class="action-title"><ClipboardCheck :size="18" /><strong>材料清单</strong></div>
    <p v-if="results.length === 0" class="workspace-muted">当前政策暂未提供完整结构化材料清单，请以官方办事指南为准。</p>
    <article v-for="material in results" :key="material.materialId" class="material-card">
      <div class="policy-card-head"><strong>{{ material.materialName }}</strong><span :class="`material-status material-status--${material.status.toLowerCase()}`">{{ materialStatusLabels[material.status] }}</span></div>
      <p>{{ policyNames[material.policyId] ?? "相关政策" }}</p>
      <p v-if="material.reason">{{ formatWorkspaceText(material.reason) }}</p>
      <p v-if="isReferenceOnly(material)" class="workspace-muted">以下材料来自历史或已结束窗口的政策记录，仅供参考，当前不可直接用于申报。</p>
      <div v-if="materialActions(material.status, isReferenceOnly(material)).length" class="material-actions">
        <button v-for="prepared in materialActions(material.status, isReferenceOnly(material))" :key="String(prepared)" type="button" :disabled="busy" @click="emit('declare', material, prepared)">{{ prepared ? "我已准备" : "还没有" }}</button>
      </div>
    </article>
  </section>
</template>
