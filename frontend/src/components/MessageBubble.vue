<script setup lang="ts">
import { computed } from "vue";
import { Bot, Globe, Pause, RotateCcw } from "@lucide/vue";
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import type { ChatMessage } from "../types/agent";

const props = defineProps<{
  message: ChatMessage;
}>();

const emit = defineEmits<{
  retry: [message: ChatMessage];
  resume: [message: ChatMessage];
}>();

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});
const renderedContent = computed(() =>
  DOMPurify.sanitize(markdown.render(props.message.content)),
);
</script>

<template>
  <article class="message-row" :class="`message-row--${message.role}`">
    <div v-if="message.role === 'assistant'" class="assistant-avatar" aria-hidden="true">
      <Bot :size="18" :stroke-width="2" />
    </div>
    <div class="message-main">
      <div v-if="message.role === 'user'" class="user-bubble">
        {{ message.content }}
      </div>
      <template v-else>
        <div
          v-if="message.status === 'sending' && message.webSearch && !message.content"
          class="searching-hint"
          role="status"
        >
          <Globe :size="14" class="searching-icon" />
          <span>联网搜索中…</span>
        </div>
        <div
          v-if="message.content"
          class="assistant-content markdown-body"
          :class="{ 'assistant-content--streaming': message.status === 'sending' }"
          v-html="renderedContent"
        ></div>
        <div
          v-if="message.sources && message.sources.length && message.status !== 'sending'"
          class="sources-block"
        >
          <p class="sources-title">搜索来源</p>
          <ol class="sources-list">
            <li v-for="(source, index) in message.sources" :key="index">
              <a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title }}</a>
            </li>
          </ol>
        </div>
        <div v-if="message.status === 'paused'" class="paused-block" role="status">
          <span class="paused-label">
            <Pause :size="13" :stroke-width="2.2" />
            已暂停生成
          </span>
          <button type="button" class="resume-button" @click="emit('resume', message)">
            继续生成
          </button>
        </div>
        <div v-if="message.status === 'sending' && !message.content" class="typing" aria-label="正在回复">
          <span></span><span></span><span></span>
        </div>
        <div v-if="message.status === 'error'" class="error-block" role="alert">
          <p>{{ message.errorMessage }}</p>
          <button type="button" class="text-button" @click="emit('retry', message)">
            <RotateCcw :size="15" />
            重试
          </button>
        </div>
      </template>
    </div>
  </article>
</template>
