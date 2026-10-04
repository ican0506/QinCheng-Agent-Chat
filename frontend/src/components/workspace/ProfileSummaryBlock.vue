<script setup lang="ts">
import { Pencil, UserRoundCheck } from "@lucide/vue";
import { computed, ref, watch } from "vue";
import { profileDisplayItems, profileMissingFields } from "../../workspace/selectors";
import type { UserProfile } from "../../types/chat";

const props = defineProps<{ profile: UserProfile; saving?: boolean; error?: string }>();
const emit = defineEmits<{ save: [profile: UserProfile] }>();
const fields = computed(() => profileDisplayItems(props.profile));
const missing = computed(() => profileMissingFields(props.profile));
const editing = ref(false);
const draft = ref<UserProfile>({});

function beginEdit(): void {
  draft.value = { ...props.profile };
  editing.value = true;
}

function cancelEdit(): void {
  editing.value = false;
  draft.value = {};
}

function save(): void {
  emit("save", { ...draft.value });
  editing.value = false;
}

function numberOrNull(value: string): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function booleanOrNull(value: string): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

watch(() => props.profile, (profile) => {
  if (!editing.value) draft.value = { ...profile };
}, { deep: true, immediate: true });
</script>

<template>
  <section class="workspace-section">
    <div class="profile-heading">
      <div class="action-title"><UserRoundCheck :size="18" /><strong>已识别画像</strong></div>
      <button v-if="!editing" type="button" class="profile-edit-button" @click="beginEdit">
        <Pencil :size="13" />编辑
      </button>
    </div>
    <p v-if="missing.length" class="profile-missing">还需要补充 {{ missing.length }} 项信息：{{ missing.join("、") }}</p>
    <p v-if="error" class="profile-error" role="alert">{{ error }}</p>
    <template v-if="editing">
      <div class="profile-form">
        <label>所在地区<input v-model.trim="draft.city" placeholder="例如：苏州市" /></label>
        <label>户籍
          <select v-model="draft.residencyRegistration">
            <option :value="null">暂未确认</option><option value="本市户籍">本市户籍</option><option value="非本市户籍">非本市户籍</option>
          </select>
        </label>
        <label>学历
          <select v-model="draft.education"><option :value="null">暂未确认</option><option value="本科">本科</option><option value="硕士">硕士</option><option value="专科">专科</option><option value="其他">其他</option></select>
        </label>
        <label>毕业年份<input :value="draft.graduationYear ?? ''" inputmode="numeric" @input="draft.graduationYear = numberOrNull(($event.target as HTMLInputElement).value)" placeholder="例如：2026" /></label>
        <label>毕业月份
          <select :value="draft.graduationMonth ?? ''" @change="draft.graduationMonth = numberOrNull(($event.target as HTMLSelectElement).value)">
            <option value="">暂未确认</option><option v-for="month in 12" :key="month" :value="month">{{ month }} 月</option>
          </select>
        </label>
        <label>当前就业状态
          <select v-model="draft.employmentStatus"><option :value="null">暂未确认</option><option value="待就业">待就业</option><option value="已就业">已就业</option><option value="创业中">创业中</option></select>
        </label>
        <label>灵活就业参保缴费
          <select :value="String(draft.flexibleEmploymentInsurance ?? '')" @change="draft.flexibleEmploymentInsurance = booleanOrNull(($event.target as HTMLSelectElement).value)"><option value="">暂未确认</option><option value="true">是</option><option value="false">否</option></select>
        </label>
        <label>创业状态
          <select :value="String(draft.entrepreneurshipIntent ?? '')" @change="draft.entrepreneurshipIntent = booleanOrNull(($event.target as HTMLSelectElement).value)"><option value="">暂未确认</option><option value="true">准备/正在创业</option><option value="false">不创业</option></select>
        </label>
      </div>
      <div class="profile-actions">
        <button type="button" class="profile-cancel" :disabled="saving" @click="cancelEdit">取消</button>
        <button type="button" class="profile-save" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存并重新判断" }}</button>
      </div>
    </template>
    <template v-else>
      <p v-if="fields.length === 0" class="workspace-muted">暂未识别到可展示的画像信息。</p>
      <dl v-else class="profile-list">
        <div v-for="field in fields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ field.value }}</dd></div>
      </dl>
    </template>
  </section>
</template>
