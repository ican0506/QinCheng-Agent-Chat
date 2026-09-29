# 前端 API 与数据契约

正式接口保持为 `POST /api/agent/chat` 与 `POST /api/agent/chat/stream`。流式事件为 `delta`、`done`、`error`；`done.data` 是 Workspace 的唯一事实来源。

`ChatData` 顶层字段：`sessionId`、`replyText`、`needFollowUp`、`followUpQuestions`、`userProfile`、`policies`、`eligibility`、`plan`、`materialResults`。

前端按 session 保存最新完整 `ChatData`，不自行推断资格或材料状态。内部规则字段由后端 session 保存，公开 `userProfile` 不承担回传内部画像的职责。

政策来源仅使用后端返回的 HTTP/HTTPS `sourceUrl`，新窗口打开并使用 `rel="noopener noreferrer"`。
