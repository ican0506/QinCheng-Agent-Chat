<script setup lang="ts">
import { UserRoundCheck } from "@lucide/vue";
import { computed } from "vue";
import { profileDisplayItems } from "../../workspace/selectors";
import type { UserProfile } from "../../types/chat";

const props = defineProps<{ profile: UserProfile }>();
const fields = computed(() => profileDisplayItems(props.profile));
</script>

<template>
  <section class="workspace-section">
    <div class="action-title"><UserRoundCheck :size="18" /><strong>已识别画像</strong></div>
    <p v-if="fields.length === 0" class="workspace-muted">暂未识别到可展示的画像信息。</p>
    <dl v-else class="profile-list">
      <div v-for="field in fields" :key="field.key">
        <dt>{{ field.label }}</dt><dd>{{ field.value }}</dd>
      </div>
    </dl>
  </section>
</template>
