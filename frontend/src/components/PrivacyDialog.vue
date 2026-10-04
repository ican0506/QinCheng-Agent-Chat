<script setup lang="ts">
import { ShieldCheck, Trash2, X } from "@lucide/vue";

defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  clear: [];
}>();

function handleClear(): void {
  if (window.confirm("确定清除全部对话记录与画像数据吗？该操作不可恢复。")) {
    emit("clear");
  }
}
</script>

<template>
  <div v-if="open" class="privacy-overlay" @click.self="emit('close')">
    <section class="privacy-dialog" role="dialog" aria-modal="true" aria-label="隐私与数据说明">
      <header class="privacy-head">
        <span class="privacy-mark"><ShieldCheck :size="18" /></span>
        <strong>隐私与数据说明</strong>
        <button type="button" class="icon-button" title="关闭" @click="emit('close')">
          <X :size="17" />
        </button>
      </header>
      <ul class="privacy-points">
        <li>
          <strong>收集内容</strong>
          <span>为匹配就业创业政策，Agent 会记录您主动提供的学历、毕业年份、就业状态、社保缴纳月数等画像信息，仅用于本应用内的资格核验与政策推荐。</span>
        </li>
        <li>
          <strong>存储方式</strong>
          <span>对话与画像保存在您的浏览器本地；服务端仅保存在内存中，服务重启后自动清除。画像数据不会共享给任何第三方。</span>
        </li>
        <li>
          <strong>随时清除</strong>
          <span>点击下方按钮可一键删除全部对话记录与画像数据，该操作不可恢复。</span>
        </li>
      </ul>
      <footer class="privacy-actions">
        <button type="button" class="privacy-clear" @click="handleClear">
          <Trash2 :size="15" />
          清除全部对话与画像
        </button>
        <button type="button" class="privacy-ok" @click="emit('close')">我知道了</button>
      </footer>
    </section>
  </div>
</template>
