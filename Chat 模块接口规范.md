# Chat 模块接口规范

## 1. 模块作用

Chat 模块负责完成第一阶段的真实对话链路：前端收集用户消息，调用 Chat API；后端保存当前进程内的会话上下文并调用 LLM；模型回答通过同一个接口返回前端。

当前模块在 ChatService 内接入固定顺序的 Python Workflow Agent Demo。它使用明确标记为 Demo 的 Mock 政策与规则生成结构化结果；不接入真实政策、RAG、数据库、OCR 或材料审核。

## 2. 整体调用流程

```text
用户
  -> Vue 对话界面
  -> POST /api/agent/chat/stream（前端默认）
  -> ChatService
  -> WorkflowAgent（Profile → PolicySearch → Eligibility → PolicyCompare → Plan）
  -> LLMProvider
  -> OpenAI 兼容的 LLM API
  -> SSE 增量事件
  -> 前端逐步展示 Markdown
```

## 3. 接口地址与请求方式

- 开发环境基础地址：`http://localhost:8000`
- API 地址：`/api/agent/chat`
- 完整地址：`http://localhost:8000/api/agent/chat`
- 请求方式：`POST`
- 请求格式：`application/json; charset=utf-8`
- 可选请求头：`X-Trace-Id`，用于端到端排查问题；不传时由后端生成
- `Authorization` 请求头已为后续鉴权预留，当前阶段不校验

原接口 `POST /api/agent/chat` 保持不变，返回一次性 JSON，供兼容调用和测试使用。前端默认调用 `POST /api/agent/chat/stream`，请求 JSON 与原接口完全相同，响应类型为 `text/event-stream`。

流式响应包含三种事件：

| 事件 | data | 含义 |
| --- | --- | --- |
| `delta` | `{ "text": "回答片段" }` | 模型新生成的文本 |
| `done` | 完整 `ApiResponse<ChatData>` | 回答完成，包含最终完整数据 |
| `error` | `ApiResponse`，`data` 为 `null` | 流式生成过程中发生错误 |

流式示例：

```text
event: delta
data: {"text":"你好"}

event: delta
data: {"text":"，我可以帮你梳理就业政策问题。"}

event: done
data: {"code":0,"message":"success","traceId":"demo-001","data":{"sessionId":"session-demo-0001","replyText":"你好，我可以帮你梳理就业政策问题。"}}
```

## 4. Request JSON

```json
{
  "sessionId": "session-0cfd3ef4-02d3-4da5-b841-e7a14d6e41a0",
  "userId": "user-b52fa61e-8bc1-4ea3-b9d0-9014b758af5c",
  "message": "我刚毕业，想了解就业政策该从哪里开始？",
  "userProfile": {
    "city": "杭州",
    "education": "本科",
    "graduationYear": 2026,
    "employmentStatus": "待就业"
  }
}
```

字段说明：

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | --- | --- |
| `sessionId` | string | 是 | 会话唯一标识，长度 8 到 128。多轮对话必须保持不变 |
| `userId` | string | 是 | 用户唯一标识。同一 `sessionId` 只能属于一个 `userId` |
| `message` | string | 是 | 本轮用户消息，长度 1 到 20000 |
| `userProfile` | object | 否 | 当前已知用户信息。省略时按空对象处理 |

`userProfile` 支持以下字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `userId` | string/null | 档案中的用户标识 |
| `city` | string/null | 所在城市 |
| `education` | string/null | `本科`、`硕士`、`专科` 或 `其他` |
| `graduationYear` | integer/null | 毕业年份 |
| `employmentStatus` | string/null | `待就业`、`已就业` 或 `创业中` |
| `isFirstTimeEntrepreneur` | boolean/null | 是否首次创业 |
| `enterpriseRegisterDate` | string/null | 企业注册日期 |
| `socialInsuranceMonths` | integer/null | 社保缴纳月数 |
| `housingStatus` | string/null | `租房`、`自有` 或 `其他` |
| `fields` | array | 扩展资料字段，包含 `key`、`value`、`source` |

## 5. Response JSON

所有成功和失败响应都使用统一外层结构：

```json
{
  "code": 0,
  "message": "success",
  "traceId": "web-92f08dfefaf84a03a59b23b1dbe069bb",
  "data": {}
}
```

外层字段说明：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `code` | integer | 业务状态码，`0` 表示成功 |
| `message` | string | 状态说明或可展示的错误信息 |
| `traceId` | string | 本次请求追踪号，排查问题时使用 |
| `data` | object/null | 成功时是业务数据，失败时为 `null` |

成功响应中的 `data` 字段：

| 字段 | 类型 | 当前阶段含义 |
| --- | --- | --- |
| `sessionId` | string | 原样返回本次会话标识 |
| `replyText` | string | LLM 生成的 Markdown 文本 |
| `needFollowUp` | boolean | 画像不完整时为 `true`，属于正常成功流程 |
| `followUpQuestions` | array | 画像不完整时返回需要补充的具体问题 |
| `userProfile` | object | 本次请求中的用户档案 |
| `policies` | array | 当前为明确标记为 Demo 的 Mock 政策结果 |
| `eligibility` | array | 当前为 Mock 规则生成的 PASS、UNKNOWN、FAIL 资格结果 |
| `plan` | object/null | 当前为 Mock Tool 生成的 Demo 办理计划；画像不完整时为 `null` |
| `materialResults` | array | 为材料审核保留，当前为空数组 |

## 6. 多轮对话如何传递

前端第一次打开会生成一个 `sessionId` 和一个持久化的 `userId`。同一对话的每次请求都继续传相同的两个值，只传本轮新增的 `message`。后端根据 `sessionId` 取出先前成功的问答并一并发给 LLM，所以前端不需要重复提交历史消息。

点击“新建对话”时，前端生成新的 `sessionId`。当前会话保存在后端进程内存中，服务重启后不会恢复；需要持久化时应替换会话存储实现，接口字段不需要改变。

## 7. 错误返回

| HTTP 状态 | code | 含义 |
| --- | --- | --- |
| 400 | `1001` | 请求字段缺失、格式错误，或 `sessionId` 与 `userId` 不匹配 |
| 200 | `2001` | 未找到匹配政策，预留给后续 RAG |
| 404 | `2002` | 政策不存在，预留给后续 RAG |
| 200 | `3001` | 材料解析失败，预留给后续 Tool |
| 500 | `5001` | LLM 未配置、认证失败、限流、连接失败或内部错误 |
| 504 | `5002` | LLM 调用超时 |

错误示例：

```json
{
  "code": 5001,
  "message": "模型服务尚未配置，请在后端 .env 中设置 LLM_API_KEY",
  "traceId": "web-92f08dfefaf84a03a59b23b1dbe069bb",
  "data": null
}
```

非流式接口通过 HTTP 错误响应返回错误；流式生成开始后的错误通过 `error` 事件返回。前端会展示 `message` 和 `traceId`，并提供重试按钮。

## 8. 如何调用

```bash
curl -X POST "http://localhost:8000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-request-001" \
  -d '{
    "sessionId": "session-demo-0001",
    "userId": "user-demo-0001",
    "message": "你好，请介绍一下你目前能提供的帮助。",
    "userProfile": {}
  }'
```

## 9. 完整响应示例

```json
{
  "code": 0,
  "message": "success",
  "traceId": "demo-request-001",
  "data": {
    "sessionId": "session-demo-0001",
    "replyText": "你好！我可以先通过对话帮你梳理就业相关的问题和个人情况。当前回答尚未经过政策知识库核验，具体政策请以官方发布为准。",
    "needFollowUp": false,
    "followUpQuestions": [],
    "userProfile": {
      "userId": null,
      "city": null,
      "education": null,
      "graduationYear": null,
      "employmentStatus": null,
      "isFirstTimeEntrepreneur": null,
      "enterpriseRegisterDate": null,
      "socialInsuranceMonths": null,
      "housingStatus": null,
      "fields": []
    },
    "policies": [],
    "eligibility": [],
    "plan": null,
    "materialResults": []
  }
}
```
