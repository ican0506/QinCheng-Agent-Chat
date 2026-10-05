import { getEligibilityByPolicyId, isPolicyMaterialReferenceOnly, profileDisplayItems, profileMissingFields, safeSourceUrl } from "../src/workspace/selectors.js";
import { prependNewSession, removeSession, saveLatestChatData } from "../src/workspace/sessionState.js";
import { materialDeclarationMessage, materialStatusLabels, materialActions } from "../src/workspace/materials.js";
import { formatWorkspaceText, missingFieldLabel } from "../src/workspace/display.js";
import { readActiveSessionId, persistActiveSessionId } from "../src/workspace/activeSession.js";
import type { ChatData } from "../src/types/chat.js";
import type { ChatSession } from "../src/types/agent.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const result: ChatData = {
  sessionId: "session-a", replyText: "已完成", needFollowUp: true, followUpQuestions: ["请补充毕业日期"],
  userProfile: { city: "苏州市", education: "本科", graduationYear: 2026 },
  policies: [{ policyId: "policy-a", name: "创业补贴", region: "苏州市", department: "人社部门", summary: "政策摘要", effectiveDate: "2026-01-01", expiryDate: null, sourceUrl: "https://example.gov.cn/policy", matchReason: "创业", conditions: [], requiredMaterials: [], process: [], isMock: false }],
  eligibility: [{ policyId: "policy-a", overallStatus: "UNKNOWN", conditionResults: [], missingFields: ["graduationDate"], summary: "缺少信息" }],
  plan: { summary: "办理计划", steps: [{ stepId: "step-a", title: "补充信息", description: "补充毕业日期", policyIds: ["policy-a"], requiredMaterials: [], actionType: "PROVIDE_INFO", priority: 10, status: "BLOCKED" }], notes: [], isMock: false }, materialResults: [],
  suggestedActions: [{ label: "看看就业见习", prompt: "就业见习适合哪些毕业生？" }],
};

const sessionA: ChatSession = { sessionId: "session-a", title: "A", messages: [] };
const sessionB: ChatSession = { sessionId: "session-b", title: "B", messages: [] };
saveLatestChatData(sessionA, result);
assert(sessionA.latestChatData === result, "done.data 应保存到当前会话");
assert(sessionB.latestChatData === undefined, "不同会话不得串用结果");
const previousResult = sessionA.latestChatData;
assert(sessionA.latestChatData === previousResult, "未收到 done.data 的错误路径不得清空上次有效结果");
assert(getEligibilityByPolicyId(result, "policy-a")?.overallStatus === "UNKNOWN", "政策应关联对应资格结果");
assert(getEligibilityByPolicyId(result, "missing") === undefined, "未关联政策不应产生资格结果");
assert(profileDisplayItems(result.userProfile).length === 3, "画像仅展示真实已返回字段");
assert(safeSourceUrl(result.policies[0].sourceUrl) !== null, "官方来源链接应可追溯");
assert(safeSourceUrl("javascript:alert(1)") === null, "非 HTTP 来源链接必须隐藏");
assert(result.plan?.steps[0]?.status === "BLOCKED", "计划步骤必须保留后端原有顺序和状态");
assert(result.suggestedActions?.[0]?.prompt === "就业见习适合哪些毕业生？", "建议操作必须使用后端给出的提示词");
assert({ ...result, policies: [], eligibility: [], plan: null }.plan === null, "空数据不得回退为模拟数据");
const material = { materialId: "policy-a:material", policyId: "policy-a", materialName: "营业执照", description: null, status: "UNKNOWN" as const, reason: "待确认", source: "POLICY" as const, userProvided: false, needsManualReview: false };
assert(materialStatusLabels.READY === "已准备" && materialStatusLabels.MANUAL_REVIEW === "需人工核验", "材料状态应使用固定中文映射");
assert(materialDeclarationMessage(material, true) === "我已经准备好营业执照", "材料操作必须生成发送给后端的自然语言声明");
assert(result.materialResults.length === 0, "空材料结果不得在前端伪造材料");
const historicalClosed: ChatData = {
  ...result,
  eligibility: [{
    policyId: "policy-a", overallStatus: "MANUAL_REVIEW", missingFields: [],
    summary: "该记录为历史通知，当前申报窗口已关闭。",
    conditionResults: [{ conditionId: "policy-validity", description: "政策时效性", status: "MANUAL_REVIEW", reason: "该记录为历史政策或历史申报通知，不能作为当前申请依据。", userEvidence: null, policyEvidence: null }],
  }],
};
assert(isPolicyMaterialReferenceOnly(historicalClosed, "policy-a"), "历史或已关闭政策的材料必须降级为只读参考");

const newSession = { sessionId: "session-new", title: "新对话", messages: [] };
const sessionsAfterCreate = prependNewSession([sessionA, sessionB], newSession);
assert(sessionsAfterCreate.length === 3, "新建任务应增加一个会话");
assert(sessionsAfterCreate[0]?.sessionId === "session-new", "新建任务应立即切换到新会话");
assert(sessionsAfterCreate[0]?.messages.length === 0, "新会话不得继承历史消息");
assert(sessionsAfterCreate[0]?.latestChatData === undefined, "新会话工作台必须为空");
assert(sessionA.latestChatData === result, "新建任务不得清空原会话工作台结果");

assert(profileMissingFields({ city: "苏州市", education: "本科", graduationYear: 2026, employmentStatus: "待就业" }).length === 0, "完整基础画像不得重复显示缺失项");
assert(profileMissingFields({ city: "苏州市", education: "本科" }).join() === "毕业年份,当前就业状态", "缺失画像只列出当前真正缺失的字段");

const removedNonActive = removeSession([sessionA, sessionB], "session-a", "session-b");
assert(removedNonActive.sessions.map((session) => session.sessionId).join() === "session-b", "删除非当前会话只移除目标会话");
assert(removedNonActive.activeSessionId === "session-b", "删除非当前会话不改变当前会话");
const removedActive = removeSession([sessionA, sessionB], "session-a", "session-a");
assert(removedActive.activeSessionId === "session-b", "删除当前会话应切换到剩余最近会话");
const removedLast = removeSession([sessionA], "session-a", "session-a");
assert(removedLast.sessions.length === 0 && removedLast.activeSessionId === "", "删除最后会话应进入空白新建任务状态");

assert(materialActions("UNKNOWN", false).join() === "true,false", "待确认材料提供两个操作");
assert(materialActions("READY", false).length === 0, "已准备材料不显示重复操作");
assert(materialActions("MISSING", false).join() === "true", "未准备材料只允许声明已准备");
assert(materialActions("MANUAL_REVIEW", false).length === 0, "人工核验材料无声明操作");
for (const status of ["UNKNOWN", "READY", "MISSING", "MANUAL_REVIEW"] as const) {
  assert(materialActions(status, true).length === 0, "历史材料任意状态都只读");
}
assert(formatWorkspaceText("政策有效性：ACTIVE；HISTORICAL；CLOSED") === "政策有效性：当前有效；历史政策；申报已结束", "枚举中文化");
assert(missingFieldLabel("residencyRegistration") === "户籍情况", "缺失字段中文化");
assert(missingFieldLabel("futureInternalField") === "需补充相关信息", "未知字段安全隐藏");
assert(formatWorkspaceText("缺少字段：flexibleEmploymentInsurance") === "缺少字段：是否已按灵活就业身份参保缴费", "原因里的字段也中文化");
assert(formatWorkspaceText("缺少字段：futureInternalField") === "缺少字段：需补充相关信息", "未知缺失字段不泄露");
const evidence = formatWorkspaceText("RAG 命中「申请条件」原文片段（相关度 0.18）：政策 ID：suzhou-test-2026 政策有效性：ACTIVE 真实申请条件。");
assert(!/RAG|0\.18|suzhou-test|ACTIVE/.test(evidence) && evidence.includes("申请条件") && evidence.includes("真实申请条件"), "隐藏算法、分数和ID，保留原文依据");
const difyEvidence = formatWorkspaceText("Dify 知识库命中原文片段：创业社会保险补贴");
assert(!/Dify|知识库/.test(difyEvidence) && difyEvidence.includes("匹配到政策原文"), "匹配依据不得泄露知识库实现");
const storage = { value: null as string | null, getItem: (_key: string) => storage.value, setItem: (_key: string, value: string) => { storage.value = value; } };
persistActiveSessionId(storage, "session-a");
assert(readActiveSessionId(storage, [sessionB, sessionA]) === "session-a", "重建后恢复选中的A而非列表首项B");
persistActiveSessionId(storage, "session-b");
assert(readActiveSessionId(storage, [sessionA, sessionB]) === "session-b", "切换B持久化");
for (const saved of [null, "", "deleted-session", "{broken-json"]) {
  storage.value = saved;
  assert(readActiveSessionId(storage, [sessionA, sessionB]) === "session-a", "无效或旧存储使用原默认选择");
}
assert(readActiveSessionId(storage, []) === "", "空会话安全处理");
const unavailable = { getItem: (_key: string): string | null => { throw new Error("disabled"); }, setItem: (_key: string, _value: string) => { throw new Error("disabled"); } };
assert(readActiveSessionId(unavailable, [sessionA]) === "session-a", "禁用存储不阻塞初始化");
persistActiveSessionId(unavailable, "session-a");
console.log("Workspace 回归测试通过");
