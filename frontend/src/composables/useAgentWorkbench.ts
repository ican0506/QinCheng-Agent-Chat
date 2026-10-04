import { computed, onMounted, ref, watch } from "vue";
import { ChatApiError, streamChatMessage } from "../services/chatApi";
import type { ChatData } from "../types/chat";
import { prependNewSession, saveLatestChatData } from "../workspace/sessionState";
import { ACTIVE_SESSION_KEY, readActiveSessionId, persistActiveSessionId } from "../workspace/activeSession";
import type {
  ChatMessage,
  ChatSession,
} from "../types/agent";

const STORAGE_KEY = "graduate-policy-agent-workbench-v1";
const USER_KEY = "graduate-policy-chat-user-v1";
const WEB_SEARCH_KEY = "graduate-policy-web-search-v1";

function createId(prefix: string): string {
  const suffix = typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${suffix}`;
}

function getOrCreateUserId(): string {
  try {
    const existing = localStorage.getItem(USER_KEY);
    if (existing) return existing;
  } catch {
    // Browsers can disable storage; the current page can still use a temporary ID.
  }
  const value = createId("user");
  try {
    localStorage.setItem(USER_KEY, value);
  } catch {
    // Keep the generated ID in memory for this page.
  }
  return value;
}

function createSession(): ChatSession {
  const sessionId = createId("session");
  return {
    sessionId,
    title: "新对话",
    messages: [],
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isChatMessage(value: unknown): value is ChatMessage {
  return isRecord(value)
    && typeof value.id === "string"
    && (value.role === "user" || value.role === "assistant")
    && typeof value.content === "string";
}

function isChatData(value: unknown): value is ChatData {
  return isRecord(value)
    && typeof value.sessionId === "string"
    && typeof value.replyText === "string"
    && typeof value.needFollowUp === "boolean"
    && Array.isArray(value.followUpQuestions)
    && isRecord(value.userProfile)
    && Array.isArray(value.policies)
    && Array.isArray(value.eligibility)
    && (value.plan === null || isRecord(value.plan))
    && Array.isArray(value.materialResults);
}

function restoreSessions(): ChatSession[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as unknown;
    if (!Array.isArray(saved)) return [];
    return saved.slice(0, 20).flatMap((value): ChatSession[] => {
      if (!isRecord(value) || typeof value.sessionId !== "string") return [];
      const messages = Array.isArray(value.messages)
        ? value.messages.filter(isChatMessage).map((message) => {
            if (message.status === "sending") {
              return { ...message, status: "error" as const, errorMessage: "上次请求已中断" };
            }
            if (message.status === "paused") {
              // 刷新后缓冲区丢失：有内容的保留已生成部分，空回复标记为已中断。
              return message.content
                ? { ...message, status: "sent" as const }
                : { ...message, status: "error" as const, errorMessage: "回答已暂停" };
            }
            return message;
          })
        : [];
      return [{
        sessionId: value.sessionId,
        title: typeof value.title === "string" ? value.title : "历史对话",
        messages,
        latestChatData: isChatData(value.latestChatData)
          ? value.latestChatData
          : undefined,
      }];
    });
  } catch {
    return [];
  }
}

function restoreWebSearchEnabled(): boolean {
  try {
    return localStorage.getItem(WEB_SEARCH_KEY) === "1";
  } catch {
    return false;
  }
}

export function useAgentWorkbench() {
  const sessions = ref<ChatSession[]>([]);
  const activeSessionId = ref("");
  const draft = ref("");
  const busy = ref(false);
  const webSearch = ref(restoreWebSearchEnabled());
  const sidebarOpen = ref(false);
  let controller: AbortController | null = null;
  const userId = getOrCreateUserId();

  // ---------------------------------------------------------------- 暂停/继续
  // 后端把完整回复通过 SSE 下发；前端用打字机渐进渲染，实现豆包/Trae 式暂停：
  // 渲染阶段暂停 = 停止显示（缓冲区保留，可继续生成）；等待阶段暂停 = 中断请求。
  let activeAssistant: ChatMessage | null = null;
  let activeSessionRef: ChatSession | null = null;
  let fullText = "";
  let renderedCount = 0;
  let renderTimer: ReturnType<typeof setInterval> | null = null;
  let pendingResponse: ChatData | null = null;
  let streamFinished = false;
  let paused = false;
  let intentionalStop = false;

  function stopTypewriter(): void {
    if (renderTimer !== null) {
      clearInterval(renderTimer);
      renderTimer = null;
    }
  }

  function cleanupStream(): void {
    stopTypewriter();
    activeAssistant = null;
    activeSessionRef = null;
    fullText = "";
    renderedCount = 0;
    pendingResponse = null;
    streamFinished = false;
    paused = false;
    intentionalStop = false;
    busy.value = false;
  }

  function finalize(): void {
    if (!activeAssistant) {
      cleanupStream();
      return;
    }
    if (pendingResponse) {
      activeAssistant.content = pendingResponse.replyText;
      activeAssistant.sources = pendingResponse.sources ?? [];
      if (activeSessionRef) saveLatestChatData(activeSessionRef, pendingResponse);
    } else {
      activeAssistant.content = fullText;
    }
    activeAssistant.status = "sent";
    cleanupStream();
  }

  function startTypewriter(): void {
    if (renderTimer !== null || paused) return;
    renderTimer = setInterval(() => {
      if (!activeAssistant) {
        cleanupStream();
        return;
      }
      if (renderedCount < fullText.length) {
        renderedCount = Math.min(fullText.length, renderedCount + 3);
        activeAssistant.content = fullText.slice(0, renderedCount);
      }
      if (renderedCount >= fullText.length && streamFinished) {
        finalize();
      }
    }, 18);
  }

  /** 暂停当前生成：渲染阶段停止显示（保留缓冲），等待阶段直接中断请求。 */
  function pause(): void {
    if (!busy.value || !activeAssistant) return;
    if (fullText.length > 0) {
      paused = true;
      stopTypewriter();
      activeAssistant.status = "paused";
      return;
    }
    intentionalStop = true;
    controller?.abort();
  }

  /** 继续生成：有缓冲内容则恢复打字机渲染；等待阶段被中断的空回复则重新发送。 */
  function resume(message: ChatMessage): void {
    if (activeAssistant && activeAssistant.id === message.id && fullText.length > 0) {
      if (!paused) return;
      paused = false;
      message.status = "sending";
      startTypewriter();
      return;
    }
    const session = activeSession.value;
    if (!session || busy.value) return;
    const index = session.messages.findIndex((item) => item.id === message.id);
    const userMessage = session.messages[index - 1];
    if (index < 1 || userMessage?.role !== "user") return;
    session.messages.splice(index - 1, 2);
    void send(userMessage.content);
  }

  const activeSession = computed(() =>
    sessions.value.find((session) => session.sessionId === activeSessionId.value),
  );
  const messages = computed(() => activeSession.value?.messages ?? []);
  const latestChatData = computed(() => activeSession.value?.latestChatData);

  function newSession(): void {
    controller?.abort();
    cleanupStream();
    const session = createSession();
    sessions.value = prependNewSession(sessions.value, session);
    activeSessionId.value = session.sessionId;
    draft.value = "";
    busy.value = false;
    sidebarOpen.value = false;
  }

  function selectSession(sessionId: string): void {
    if (sessionId === activeSessionId.value) {
      sidebarOpen.value = false;
      return;
    }
    controller?.abort();
    cleanupStream();
    activeSessionId.value = sessionId;
    draft.value = "";
    busy.value = false;
    sidebarOpen.value = false;
  }

  function updateTitle(session: ChatSession, text: string): void {
    if (session.title !== "新对话") return;
    const normalized = text.replace(/\s+/g, " ").trim();
    session.title = normalized.length > 18 ? `${normalized.slice(0, 18)}…` : normalized;
  }

  function setWebSearchEnabled(value: boolean): void {
    webSearch.value = value;
    try {
      localStorage.setItem(WEB_SEARCH_KEY, value ? "1" : "0");
    } catch {
      // Storage failure only affects persistence, not the current toggle.
    }
  }

  async function send(text = draft.value): Promise<void> {
    const content = text.trim();
    const session = activeSession.value;
    if (!content || busy.value || !session) return;

    updateTitle(session, content);
    const userMessage: ChatMessage = {
      id: createId("message"),
      role: "user",
      content,
      status: "sent",
    };
    const assistantIndex = session.messages.push(userMessage, {
      id: createId("message"),
      role: "assistant",
      content: "",
      status: "sending",
      webSearch: webSearch.value,
    }) - 1;
    const assistantMessage = session.messages[assistantIndex];
    draft.value = "";
    busy.value = true;
    const requestController = new AbortController();
    controller = requestController;
    activeAssistant = assistantMessage;
    activeSessionRef = session;
    fullText = "";
    renderedCount = 0;
    pendingResponse = null;
    streamFinished = false;
    paused = false;
    intentionalStop = false;

    try {
      const response = await streamChatMessage(
        {
          sessionId: session.sessionId,
          userId,
          message: content,
          userProfile: session.latestChatData?.userProfile ?? {},
          webSearch: webSearch.value,
        },
        (chunk) => {
          fullText += chunk;
          startTypewriter();
        },
        requestController.signal,
      );
      pendingResponse = response;
      streamFinished = true;
      // done 已到达：若渲染已追平缓冲则立即收尾，否则由打字机在追平时收尾。
      if (renderedCount >= fullText.length) finalize();
    } catch (error) {
      streamFinished = true;
      if (intentionalStop) {
        // 用户在等待阶段主动暂停：保留空回复并标记暂停态，可“继续生成”（重新发送）。
        assistantMessage.status = "paused";
        cleanupStream();
        return;
      }
      if (fullText.length > 0) {
        // 流中途异常但已有部分内容：按暂停处理，已生成内容保留。
        assistantMessage.status = "paused";
        cleanupStream();
        return;
      }
      assistantMessage.status = "error";
      if (error instanceof DOMException && error.name === "AbortError") {
        assistantMessage.errorMessage = "回答已停止";
      } else {
        const apiError = error instanceof ChatApiError ? error : null;
        assistantMessage.errorMessage = apiError?.traceId
          ? `${apiError.message}（追踪号：${apiError.traceId}）`
          : apiError?.message ?? "请求失败，请稍后重试";
      }
      cleanupStream();
    } finally {
      if (controller === requestController) {
        controller = null;
      }
    }
  }

  function retry(message: ChatMessage): void {
    const session = activeSession.value;
    if (!session || busy.value) return;
    const index = session.messages.findIndex((item) => item.id === message.id);
    const userMessage = session.messages[index - 1];
    if (index < 1 || userMessage?.role !== "user") return;
    session.messages.splice(index - 1, 2);
    void send(userMessage.content);
  }

  watch(
    sessions,
    (value) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      } catch {
        // Storage failure must not interrupt the active conversation.
      }
    },
    { deep: true },
  );

  watch(activeSessionId, (value) => persistActiveSessionId(localStorage, value), { flush: "sync" });

  onMounted(() => {
    sessions.value = restoreSessions();
    if (sessions.value.length === 0) newSession();
    else activeSessionId.value = readActiveSessionId(localStorage, sessions.value);
  });

  /** 清除全部本地数据（对话记录、画像、用户标识）并重置为全新会话。 */
  function clearAllData(): void {
    controller?.abort();
    cleanupStream();
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ACTIVE_SESSION_KEY);
    const session = createSession();
    sessions.value = [session];
    activeSessionId.value = session.sessionId;
    draft.value = "";
    busy.value = false;
  }

  return {
    sessions,
    activeSession,
    activeSessionId,
    messages,
    latestChatData,
    draft,
    busy,
    webSearch,
    setWebSearchEnabled,
    sidebarOpen,
    newSession,
    selectSession,
    send,
    pause,
    resume,
    retry,
    clearAllData,
  };
}
