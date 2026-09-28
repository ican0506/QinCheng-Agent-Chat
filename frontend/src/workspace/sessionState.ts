import type { ChatData } from "../types/chat.js";
import type { ChatSession } from "../types/agent.js";

/** 仅在 SSE done 收到完整 ChatData 后归档，不应在错误路径调用。 */
export function saveLatestChatData(session: ChatSession, data: ChatData): void {
  session.latestChatData = data;
}
