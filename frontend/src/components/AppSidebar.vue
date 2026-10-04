<script setup lang="ts">
import { GraduationCap, MessageSquare, MoreHorizontal, Plus, ShieldCheck, Trash2, X } from "@lucide/vue";
import { ref } from "vue";
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
  deleteSession: [sessionId: string];
  privacy: [];
}>();

const deletingMenuFor = ref("");

function requestDelete(sessionId: string): void {
  deletingMenuFor.value = "";
  if (window.confirm("删除后，该会话中的消息、画像和分析结果将被删除。")) {
    emit("deleteSession", sessionId);
  }
}
</script>

<template>
  <div v-if="open" class="sidebar-scrim" @click="emit('close')"></div>
  <aside class="sidebar" :class="{ 'sidebar--open': open }">
    <div class="brand-row">
      <div class="brand-mark"><GraduationCap :size="21" /></div>
      <div class="brand-copy">
        <strong>青程 Agent</strong>
        <span>高校毕业生就业创业政策智能助手</span>
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
      <p class="sidebar-label">最近任务</p>
      <div
        v-for="session in sessions"
        :key="session.sessionId"
        class="history-item"
        :class="{ 'history-item--active': session.sessionId === activeSessionId }"
      >
        <button type="button" class="history-select" :aria-current="session.sessionId === activeSessionId ? 'page' : undefined" @click="emit('selectSession', session.sessionId)">
          <MessageSquare :size="16" />
          <span class="history-copy">
            <strong>{{ session.title }}</strong>
            <small>{{ session.latestChatData ? (session.latestChatData.needFollowUp ? "等待补充信息" : "已获得分析结果") : "等待咨询" }}</small>
          </span>
        </button>
        <div class="history-menu">
          <button type="button" class="history-menu-trigger" title="会话操作" @click="deletingMenuFor = deletingMenuFor === session.sessionId ? '' : session.sessionId"><MoreHorizontal :size="16" /></button>
          <button v-if="deletingMenuFor === session.sessionId" type="button" class="history-delete" @click="requestDelete(session.sessionId)"><Trash2 :size="13" />删除对话</button>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <p class="sidebar-footer-line">
        <ShieldCheck :size="17" />
        <span>政策结论须以官方数据为准</span>
      </p>
      <button type="button" class="privacy-entry" @click="emit('privacy')">
        <ShieldCheck :size="14" />
        隐私与数据
      </button>
    </div>
  </aside>
</template>
