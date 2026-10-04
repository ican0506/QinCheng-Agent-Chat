import type { ApiResponse, ChatData, ChatRequest, UserProfile } from "../types/chat";

export class ChatApiError extends Error {
  constructor(
    message: string,
    readonly traceId?: string,
  ) {
    super(message);
    this.name = "ChatApiError";
  }
}

function createTraceId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function sendChatMessage(
  payload: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatData> {
  const fallbackTraceId = createTraceId();
  let response: Response;

  try {
    response = await fetch("/api/agent/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trace-Id": fallbackTraceId,
      },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ChatApiError("无法连接对话服务，请检查服务是否已启动", fallbackTraceId);
  }

  let body: ApiResponse<ChatData>;
  try {
    body = (await response.json()) as ApiResponse<ChatData>;
  } catch {
    throw new ChatApiError("服务返回了无法识别的响应", fallbackTraceId);
  }

  if (!response.ok || body.code !== 0 || !body.data) {
    throw new ChatApiError(body.message || "请求失败，请稍后重试", body.traceId);
  }
  return body.data;
}

export async function updateSessionProfile(
  sessionId: string,
  userId: string,
  profile: UserProfile,
): Promise<ChatData> {
  return requestJson<ChatData>(`/api/agent/sessions/${encodeURIComponent(sessionId)}/profile`, {
    method: "PUT",
    body: JSON.stringify({ userId, profile }),
  });
}

export async function deleteAgentSession(sessionId: string, userId: string): Promise<boolean> {
  const response = await requestJson<{ deleted: boolean }>(
    `/api/agent/sessions/${encodeURIComponent(sessionId)}?userId=${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
  return response.deleted;
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const fallbackTraceId = createTraceId();
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "X-Trace-Id": fallbackTraceId,
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ChatApiError("无法连接对话服务，请检查服务是否已启动", fallbackTraceId);
  }
  let body: ApiResponse<T>;
  try {
    body = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new ChatApiError("服务返回了无法识别的响应", fallbackTraceId);
  }
  if (!response.ok || body.code !== 0 || !body.data) {
    throw new ChatApiError(body.message || "请求失败，请稍后重试", body.traceId);
  }
  return body.data;
}

interface StreamDelta {
  text?: string;
}

function parseEventBlock(block: string): { event: string; data: unknown } | null {
  const lines = block.split("\n");
  const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!event || !data) return null;
  return { event, data: JSON.parse(data) as unknown };
}

export async function streamChatMessage(
  payload: ChatRequest,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<ChatData> {
  const fallbackTraceId = createTraceId();
  let response: Response;
  try {
    response = await fetch("/api/agent/chat/stream", {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        "X-Trace-Id": fallbackTraceId,
      },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ChatApiError("无法连接对话服务，请检查服务是否已启动", fallbackTraceId);
  }

  if (!response.ok) {
    try {
      const body = (await response.json()) as ApiResponse<never>;
      throw new ChatApiError(body.message || "请求失败，请稍后重试", body.traceId);
    } catch (error) {
      if (error instanceof ChatApiError) throw error;
      throw new ChatApiError("对话服务暂时不可用，请稍后重试", fallbackTraceId);
    }
  }
  if (!response.body) {
    throw new ChatApiError("浏览器无法读取流式响应，请重试", fallbackTraceId);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatData | null = null;

  const handleBlock = (block: string): void => {
    let parsed: { event: string; data: unknown } | null;
    try {
      parsed = parseEventBlock(block);
    } catch {
      throw new ChatApiError("服务返回了无法识别的流式响应", fallbackTraceId);
    }
    if (!parsed) return;
    if (parsed.event === "delta") {
      const delta = parsed.data as StreamDelta;
      if (typeof delta.text === "string") onDelta(delta.text);
      return;
    }
    const envelope = parsed.data as ApiResponse<ChatData>;
    if (parsed.event === "error") {
      throw new ChatApiError(envelope.message || "请求失败，请稍后重试", envelope.traceId);
    }
    if (parsed.event === "done" && envelope.code === 0 && envelope.data) {
      result = envelope.data;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    buffer = buffer.replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      handleBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) handleBlock(buffer);
  if (!result) throw new ChatApiError("流式响应意外中断，请重试", fallbackTraceId);
  return result;
}
