import type { ChatData } from "./chat.js";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "sending" | "sent" | "error";
  errorMessage?: string;
}

export interface ChatSession {
  sessionId: string;
  title: string;
  messages: ChatMessage[];
  /** 当前会话最近一次 SSE done.data；工作台唯一的数据来源。 */
  latestChatData?: ChatData;
}
