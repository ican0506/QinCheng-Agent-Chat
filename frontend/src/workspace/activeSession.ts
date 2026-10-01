import type { ChatSession } from "../types/agent.js";

export const ACTIVE_SESSION_KEY = "graduate-policy-active-session-v1";
type SessionStorage = Pick<Storage, "getItem" | "setItem">;

export function readActiveSessionId(storage: SessionStorage, sessions: ChatSession[]): string {
  try {
    const saved = storage.getItem(ACTIVE_SESSION_KEY);
    if (sessions.some((session) => session.sessionId === saved)) return saved!;
  } catch {
    // 存储被禁用时仍允许正常咨询。
  }
  return sessions[0]?.sessionId ?? "";
}

export function persistActiveSessionId(storage: SessionStorage, sessionId: string): void {
  try {
    storage.setItem(ACTIVE_SESSION_KEY, sessionId);
  } catch {
    // 不影响会话内存状态，也不清除聊天历史。
  }
}
