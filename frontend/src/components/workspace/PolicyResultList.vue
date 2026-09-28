<script setup lang="ts">
import { BookOpenCheck, ExternalLink } from "@lucide/vue";
import { getEligibilityByPolicyId, safeSourceUrl } from "../../workspace/selectors";
import type { ChatData, EligibilityStatus, PolicyCandidate } from "../../types/chat";

defineProps<{ policies: PolicyCandidate[]; data: ChatData }>();
const statusLabels: Record<EligibilityStatus, string> = { PASS: "基本符合", FAIL: "当前不符合", UNKNOWN: "信息不足", MANUAL_REVIEW: "需要人工核验" };
</script>

<template>
  <section class="workspace-section">
    <div class="action-title"><BookOpenCheck :size="18" /><strong>政策匹配</strong></div>
    <p v-if="policies.length === 0" class="workspace-muted">本次未找到匹配的政策。</p>
    <article v-for="policy in policies" :key="policy.policyId" class="policy-card">
      <div class="policy-card-head">
        <strong>{{ policy.name }}</strong>
        <span v-if="getEligibilityByPolicyId(data, policy.policyId)" :class="`policy-status policy-status--${getEligibilityByPolicyId(data, policy.policyId)?.overallStatus.toLowerCase()}`">{{ statusLabels[getEligibilityByPolicyId(data, policy.policyId)!.overallStatus] }}</span>
      </div>
      <p>{{ policy.summary }}</p>
      <p v-if="policy.matchReason" class="match-reason">匹配依据：{{ policy.matchReason }}</p>
      <dl class="policy-meta">
        <div><dt>地区</dt><dd>{{ policy.region }}</dd></div>
        <div><dt>主管部门</dt><dd>{{ policy.department }}</dd></div>
        <div><dt>生效时间</dt><dd>{{ policy.effectiveDate || "--" }}</dd></div>
        <div><dt>官方来源</dt><dd><a v-if="safeSourceUrl(policy.sourceUrl)" :href="safeSourceUrl(policy.sourceUrl) ?? undefined" target="_blank" rel="noopener noreferrer">查看来源<ExternalLink :size="10" /></a><template v-else>暂无链接</template></dd></div>
      </dl>
      <div v-if="getEligibilityByPolicyId(data, policy.policyId)" class="eligibility-detail">
        <strong>资格辅助判断：{{ statusLabels[getEligibilityByPolicyId(data, policy.policyId)!.overallStatus] }}</strong>
        <p>{{ getEligibilityByPolicyId(data, policy.policyId)!.summary }}</p>
        <ul v-if="getEligibilityByPolicyId(data, policy.policyId)!.conditionResults.length">
          <li v-for="condition in getEligibilityByPolicyId(data, policy.policyId)!.conditionResults" :key="condition.conditionId">
            <b>{{ condition.description }}</b>：{{ statusLabels[condition.status] }}<span v-if="condition.reason">，{{ condition.reason }}</span>
            <small v-if="condition.userEvidence">用户信息：{{ condition.userEvidence }}</small>
            <small v-if="condition.policyEvidence">政策依据：{{ condition.policyEvidence }}</small>
          </li>
        </ul>
      </div>
    </article>
  </section>
</template>
