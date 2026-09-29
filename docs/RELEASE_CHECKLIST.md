# 发布检查清单

## 比赛前环境

- [ ] `backend/.env` 已在本机配置，且 API Key 有效（不提交）。
- [ ] 后端与前端均已启动，Swagger 可访问。
- [ ] 浏览器缩放为 100%，网络可用。

## 比赛场景

- [ ] 按 `COMPETITION_SCENARIOS.md` 依次运行 A–E。
- [ ] 确认官方来源入口可打开；打不开不影响本地结构化结果展示。

## 降级验证

- [ ] LLM 不可用时仍返回结构化结果与模板说明。
- [ ] RAG 异常时回退 LocalPolicySearchTool。
- [ ] RAG 正常但零命中时保持空结果。
- [ ] SSE 的 LLM 失败仍返回 `done.data`。
