<script setup lang="ts">
import { ref } from "vue";
import { MessagesSquare, PanelRight } from "@lucide/vue";
import AppSidebar from "./components/AppSidebar.vue";
import ChatPanel from "./components/ChatPanel.vue";
import AgentWorkspace from "./components/workspace/AgentWorkspace.vue";
import { useAgentWorkbench } from "./composables/useAgentWorkbench";

const suggestions = [
  "我是今年毕业生，想了解本地就业补贴",
  "签订劳动合同后，还能申请哪些就业政策？",
  "咨询应届毕业生就业政策需要准备哪些信息？",
];

const mobileView = ref<"chat" | "workspace">("chat");
const {
  sessions,
  activeSession,
  activeSessionId,
  messages,
  latestChatData,
  draft,
  busy,
  sidebarOpen,
  newSession,
  selectSession,
  send,
  retry,
} = useAgentWorkbench();
const chatPanel = ref<InstanceType<typeof ChatPanel> | null>(null);

function startSession(): void {
  newSession();
  mobileView.value = "chat";
}

function handleFollowUp(question: string): void {
  draft.value = "";
  mobileView.value = "chat";
  chatPanel.value?.focusComposer(question);
}
</script>

<template>
  <div class="app-shell">
    <AppSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :open="sidebarOpen"
      @close="sidebarOpen = false"
      @new-session="startSession"
      @select-session="selectSession"
    />

    <main class="agent-main">
      <nav class="mobile-view-switcher" aria-label="工作区视图">
        <button type="button" :class="{ active: mobileView === 'chat' }" :aria-pressed="mobileView === 'chat'" @click="mobileView = 'chat'">
          <MessagesSquare :size="16" />对话
        </button>
        <button type="button" :class="{ active: mobileView === 'workspace' }" :aria-pressed="mobileView === 'workspace'" @click="mobileView = 'workspace'">
          <PanelRight :size="16" />工作台
        </button>
      </nav>

      <div v-if="activeSession" class="agent-columns">
        <ChatPanel
          ref="chatPanel"
          :class="{ 'mobile-view-hidden': mobileView !== 'chat' }"
          :title="activeSession.title"
          :messages="messages"
          :draft="draft"
          :busy="busy"
          :suggestions="suggestions"
          @open-sidebar="sidebarOpen = true"
          @update:draft="draft = $event"
          @send="send($event)"
          @retry="retry"
        />
        <AgentWorkspace
          :class="{ 'mobile-view-hidden': mobileView !== 'workspace' }"
          :data="latestChatData"
          :busy="busy"
          @follow-up="handleFollowUp"
        />
      </div>
    </main>
  </div>
</template>
