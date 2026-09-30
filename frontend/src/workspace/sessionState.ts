import type { ChatData } from "../types/chat.js";
import type { ChatSession } from "../types/agent.js";

/** 以不可变方式插入空会话，避免复用旧会话的消息或工作台状态。 */
export function prependNewSession(
  sessions: ChatSession[],
  session: ChatSession,
): ChatSession[] {
  return [session, ...sessions];
}

/** 仅在 SSE done 收到完整 ChatData 后归档，不应在错误路径调用。 */
export function saveLatestChatData(session: ChatSession, data: ChatData): void {
  session.latestChatData = data;
}
