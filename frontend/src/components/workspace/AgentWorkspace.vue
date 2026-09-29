<script setup lang="ts">
import { PanelRight } from "@lucide/vue";
import FollowUpBlock from "./FollowUpBlock.vue";
import MaterialChecklist from "./MaterialChecklist.vue";
import PlanTimeline from "./PlanTimeline.vue";
import PolicyResultList from "./PolicyResultList.vue";
import ProfileSummaryBlock from "./ProfileSummaryBlock.vue";
import type { ChatData, MaterialResult } from "../../types/chat";
import { computed } from "vue";

const props = defineProps<{ data?: ChatData; busy: boolean }>();
const emit = defineEmits<{ followUp: [question: string]; materialDeclare: [materialId: string, prepared: boolean] }>();
const policyNames = computed(() => Object.fromEntries((props.data?.policies ?? []).map((policy) => [policy.policyId, policy.name])));
function declareMaterial(material: MaterialResult, prepared: boolean): void {
  emit("materialDeclare", material.materialId, prepared);
}
</script>

<template>
  <aside class="agent-workspace">
    <header class="panel-topbar workspace-topbar">
      <PanelRight :size="19" />
      <div class="panel-heading-copy">
        <strong>Agent 工作台</strong>
        <span>{{ busy ? "Agent 正在分析…" : data ? "基于最近一次 Agent 结果" : "等待咨询" }}</span>
      </div>
    </header>

    <div class="workspace-scroll">
      <div v-if="!data && !busy" class="workspace-empty">
        <strong>尚未咨询</strong>
        <p>发送问题后，这里会展示政策匹配、资格辅助判断和办理计划。</p>
      </div>
      <div v-else-if="busy && !data" class="workspace-empty">
        <strong>Agent 正在分析…</strong><p>结果将在本次回复完成后显示。</p>
      </div>
      <template v-if="data">
        <ProfileSummaryBlock :profile="data.userProfile" />
        <FollowUpBlock v-if="data.needFollowUp && data.followUpQuestions.length" :questions="data.followUpQuestions" @select="emit('followUp', $event)" />
        <PolicyResultList :policies="data.policies" :data="data" />
        <MaterialChecklist :results="data.materialResults" :policy-names="policyNames" :busy="busy" @declare="declareMaterial" />
        <PlanTimeline :plan="data.plan" />
      </template>
    </div>
  </aside>
</template>
