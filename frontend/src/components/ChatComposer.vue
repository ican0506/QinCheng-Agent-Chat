<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { ArrowUp, Globe, Square } from "@lucide/vue";

const props = defineProps<{
  modelValue: string;
  busy: boolean;
  webSearch: boolean;
  inputHint?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  "update:webSearch": [value: boolean];
  send: [];
  pause: [];
}>();

const textarea = ref<HTMLTextAreaElement | null>(null);

function resize(): void {
  const element = textarea.value;
  if (!element) return;
  element.style.height = "auto";
  element.style.height = `${Math.min(element.scrollHeight, 180)}px`;
}

function update(event: Event): void {
  emit("update:modelValue", (event.target as HTMLTextAreaElement).value);
  resize();
}

function keydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    // 生成过程中 Enter = 暂停（豆包/Trae 交互一致）；空闲时 Enter = 发送。
    if (props.busy) {
      emit("pause");
      return;
    }
    if (props.modelValue.trim()) emit("send");
  }
}

function focus(inputHint?: string): void {
  const element = textarea.value;
  if (!element) return;
  element.focus();
  if (inputHint) element.placeholder = inputHint;
}

defineExpose({ focus });

watch(
  () => props.modelValue,
  async () => {
    await nextTick();
    resize();
  },
);
</script>

<template>
  <div class="composer-shell">
    <textarea
      ref="textarea"
      :value="modelValue"
      rows="1"
      maxlength="20000"
      :placeholder="inputHint || '输入你想了解的问题'"
      aria-label="消息输入框"
      @input="update"
      @keydown="keydown"
    ></textarea>
    <div class="composer-toolbar">
      <button
        type="button"
        class="web-toggle"
        :class="{ active: webSearch }"
        :aria-pressed="webSearch"
        title="开启后，Agent 可检索全网最新公开信息并在回复中附来源链接"
        @click="emit('update:webSearch', !props.webSearch)"
      >
        <Globe :size="14" :stroke-width="2" />
        <span>联网搜索</span>
      </button>
    </div>
    <button
      v-if="busy"
      type="button"
      class="send-button send-button--stop"
      title="暂停生成"
      aria-label="暂停生成"
      @click="emit('pause')"
    >
      <Square :size="14" :stroke-width="0" fill="currentColor" />
    </button>
    <button
      v-else
      type="button"
      class="send-button"
      :disabled="!modelValue.trim()"
      title="发送"
      aria-label="发送"
      @click="emit('send')"
    >
      <ArrowUp :size="19" :stroke-width="2.4" />
    </button>
  </div>
</template>
