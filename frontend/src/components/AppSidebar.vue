<script setup lang="ts">
import { GraduationCap, MessageSquare, Plus, ShieldCheck, X } from "@lucide/vue";
import type { ChatSession } from "../types/agent";

defineProps<{
  sessions: ChatSession[];
  activeSessionId: string;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  newSession: [];
  selectSession: [sessionId: string];
}>();
</script>

<template>
  <div v-if="open" class="sidebar-scrim" @click="emit('close')"></div>
  <aside class="sidebar" :class="{ 'sidebar--open': open }">
    <div class="brand-row">
      <div class="brand-mark"><GraduationCap :size="21" /></div>
      <div class="brand-copy">
        <strong>青程 Agent</strong>
        <span>应届毕业生就业政策</span>
      </div>
      <button class="icon-button sidebar-close" type="button" title="关闭侧栏" @click="emit('close')">
        <X :size="19" />
      </button>
    </div>

    <button class="new-chat-button" type="button" @click="emit('newSession')">
      <Plus :size="17" />
      新建任务
    </button>

    <div class="history-section">
      <p class="sidebar-label">正在处理</p>
      <button
        v-for="session in sessions"
        :key="session.sessionId"
        type="button"
        class="history-item"
        :class="{ 'history-item--active': session.sessionId === activeSessionId }"
        :aria-current="session.sessionId === activeSessionId ? 'page' : undefined"
        @click="emit('selectSession', session.sessionId)"
      >
        <MessageSquare :size="16" />
        <span class="history-copy">
          <strong>{{ session.title }}</strong>
          <small>{{ session.latestChatData ? (session.latestChatData.needFollowUp ? "等待补充信息" : "已获得分析结果") : "等待咨询" }}</small>
        </span>
      </button>
    </div>

    <div class="sidebar-footer">
      <ShieldCheck :size="17" />
      <span>政策结论须以官方数据为准</span>
    </div>
  </aside>
</template>
