<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { ArrowUp } from "@lucide/vue";

const props = defineProps<{
  modelValue: string;
  busy: boolean;
  inputHint?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  send: [];
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
    if (!props.busy && props.modelValue.trim()) emit("send");
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
    <button
      type="button"
      class="send-button"
      :disabled="busy || !modelValue.trim()"
      title="发送"
      aria-label="发送"
      @click="emit('send')"
    >
      <ArrowUp :size="19" :stroke-width="2.4" />
    </button>
  </div>
</template>
