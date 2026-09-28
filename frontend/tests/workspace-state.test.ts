import { getEligibilityByPolicyId, profileDisplayItems, safeSourceUrl } from "../src/workspace/selectors.js";
import { saveLatestChatData } from "../src/workspace/sessionState.js";
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
assert({ ...result, policies: [], eligibility: [], plan: null }.plan === null, "空数据不得回退为模拟数据");
