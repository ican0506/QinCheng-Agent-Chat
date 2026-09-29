<script setup lang="ts">
import { CircleHelp } from "@lucide/vue";
defineProps<{ questions: string[] }>();
const emit = defineEmits<{ select: [question: string] }>();
</script>

<template>
  <section class="workspace-section action-section">
    <div class="action-title"><CircleHelp :size="18" /><strong>还需要补充 {{ questions.length }} 项信息</strong></div>
    <p>这些问题来自后端资格判断。选择问题后，请在输入框中填写你的实际情况。</p>
    <div class="follow-up-list"><button v-for="question in questions" :key="question" type="button" @click="emit('select', question)">{{ question }}</button></div>
  </section>
</template>
