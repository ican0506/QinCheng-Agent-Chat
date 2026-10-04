import type { ChatData, WebSource } from "./chat.js";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** paused：用户在生成过程中暂停（内容可能不完整，可继续生成）。 */
  status?: "sending" | "paused" | "sent" | "error";
  errorMessage?: string;
  /** 该条消息发送时是否开启了联网搜索（用于展示“联网搜索中”状态）。 */
  webSearch?: boolean;
  /** 联网搜索引用来源。 */
  sources?: WebSource[];
}

export interface ChatSession {
  sessionId: string;
  title: string;
  messages: ChatMessage[];
  /** 当前会话最近一次 SSE done.data；工作台唯一的数据来源。 */
  latestChatData?: ChatData;
}
