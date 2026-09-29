<script setup lang="ts">
import { ClipboardCheck } from "@lucide/vue";
import { materialStatusLabels } from "../../workspace/materials";
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
      <p>{{ policyNames[material.policyId] ?? material.policyId }}</p>
      <p v-if="material.reason">{{ material.reason }}</p>
      <p v-if="isReferenceOnly(material)" class="workspace-muted">以下材料来自历史或已结束窗口的政策记录，仅供参考，当前不可直接用于申报。</p>
      <div v-else class="material-actions">
        <button type="button" :disabled="busy" @click="emit('declare', material, true)">我已准备</button>
        <button type="button" :disabled="busy" @click="emit('declare', material, false)">还没有</button>
      </div>
    </article>
  </section>
</template>
