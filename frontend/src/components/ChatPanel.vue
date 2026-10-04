<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { Menu, Sparkles } from "@lucide/vue";
import ChatComposer from "./ChatComposer.vue";
import MessageBubble from "./MessageBubble.vue";
import type { ChatMessage } from "../types/agent";

const props = defineProps<{
  title: string;
  messages: ChatMessage[];
  draft: string;
  busy: boolean;
  webSearch: boolean;
  suggestions: string[];
}>();

const emit = defineEmits<{
  openSidebar: [];
  "update:draft": [value: string];
  "update:webSearch": [value: boolean];
  send: [text?: string];
  retry: [message: ChatMessage];
  pause: [];
  resume: [message: ChatMessage];
}>();

const messageList = ref<HTMLElement | null>(null);
const composer = ref<InstanceType<typeof ChatComposer> | null>(null);

async function scrollToBottom(): Promise<void> {
  await nextTick();
  messageList.value?.scrollTo({
    top: messageList.value.scrollHeight,
    behavior: "smooth",
  });
}

function useSuggestion(text: string): void {
  emit("update:draft", text);
  emit("send", text);
}

function focusComposer(inputHint?: string): void {
  composer.value?.focus(inputHint);
}

defineExpose({ focusComposer });

watch(
  () => props.messages,
  () => void scrollToBottom(),
  { deep: true, immediate: true },
);
</script>

<template>
  <section class="chat-panel">
    <header class="panel-topbar chat-topbar">
      <button class="icon-button sidebar-trigger" type="button" title="打开会话列表" @click="emit('openSidebar')">
        <Menu :size="20" />
      </button>
      <div class="panel-heading-copy">
        <strong>{{ title }}</strong>
        <span><i></i>{{ busy ? "Agent 正在回复" : "Agent 对话" }}</span>
      </div>
    </header>

    <div ref="messageList" class="message-list" aria-live="polite">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon"><Sparkles :size="23" /></div>
        <h1>从你的就业目标开始</h1>
        <p>描述个人情况和想了解的政策，Agent 会逐步补充所需信息。</p>
        <div class="suggestions">
          <button v-for="item in suggestions" :key="item" type="button" @click="useSuggestion(item)">
            <span>{{ item }}</span>
            <span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
      <div v-else class="message-container">
        <MessageBubble
          v-for="message in messages"
          :key="message.id"
          :message="message"
          @retry="emit('retry', $event)"
          @resume="emit('resume', $event)"
        />
      </div>
    </div>

    <footer class="composer-area">
      <div class="composer-container">
        <ChatComposer
          ref="composer"
          :model-value="draft"
          :busy="busy"
          :web-search="webSearch"
          @update:model-value="emit('update:draft', $event)"
          @update:web-search="emit('update:webSearch', $event)"
          @send="emit('send')"
          @pause="emit('pause')"
        />
        <p class="disclaimer">具体政策以当地官方发布和后续政策库检索结果为准</p>
      </div>
    </footer>
  </section>
</template>
