# 前端架构

Vue 工作台由 `useAgentWorkbench` 管理会话、聊天记录与每个 session 的 `latestChatData`。

```text
SSE done.data → session.latestChatData → AgentWorkspace
```

Workspace 只展示后端真实返回的用户画像、追问、政策、资格判断、材料清单与办理计划。点击补充问题只聚焦输入框；点击材料状态只发送自然语言声明，再等待新的 SSE `done.data` 更新界面。

没有前端 Mock Workspace、文件上传或本地资格/材料状态计算。
