# Agent 自主决策回复引擎（Agent Reply Engine）实施方案

## Context（背景）

当前项目的对话回复本质是：确定性 Workflow 跑完后，由 `FinalExplanationPolicy` 决定"是否值得调用 LLM"；大部分场景（FOLLOW_UP / FACT_QUERY 画像不足 / NO_POLICY / REALTIME_STATUS_ONLY / MATERIAL_UPDATE / HISTORICAL_ONLY / OUT_OF_SCOPE）直接跳过 LLM，输出 `chat_service.py` 里的固定模板（如"已完成初步政策分析，还需要补充以下信息后才能继续判断：…"）。

用户需求：把回复升级为**具备自主决策能力的 agent 模式**——
1. 动态理解用户输入（不依赖固定模式）；
2. LLM 自主调用后端资源/工具（政策检索、资格核验、材料、实时搜索）后再回答；
3. 上下文感知（结合历史对话）；
4. 不同场景灵活调整回复策略。

**设计原则**（延续项目安全底线）：业务事实（政策、资格 PASS/FAIL、材料、计划）仍由确定性工具产生，LLM 只能通过工具获取事实、自主组织回复；所有 LLM 输出经过"事实接地（grounding）校验"，校验失败自动回退现有确定性模板。前端契约（ChatData / SSE delta-done-error）完全不变，前端零改动。

## 架构

```
用户请求 → 确定性 Workflow（不变，产出 GovernmentAgentState）
        → AgentReplyPolicy.decide(state)   # 新：决定是否启用 agent 回复
        → AgentReplyEngine（新）
             场景化策略提示 + 历史 messages
             → LLM complete_with_tools(tools)
             ← LLM 自主决定调用 read-only 工具（≤3 轮）
             ← LLM 生成最终回复
             → Grounding 校验（政策名/ID 必须来自 State 或工具结果）
             ✗ 失败/超时/异常 → 现有 _fallback_reply 模板
```

## 修改清单

### 1. LLM Provider 支持 function calling

**`backend/app/services/llm/base.py`**
- 新增 `AgentMessage = dict[str, Any]`（允许 `role="tool"`、`tool_calls`、`tool_call_id`，OpenAI SDK 直接收 dict）。
- `LLMProvider` 新增：
  - `supports_tools` 属性，默认 `False`（**保证现有测试 Fake Provider 走旧路径，全部不破坏**）；
  - `async def complete_with_tools(messages, tools) -> AgentToolResponse`，默认抛 `NotImplementedError`。
- 新增 `@dataclass AgentToolResponse`：`content: str | None`、`tool_calls: list[AgentToolCall]`；`AgentToolCall`：`id/name/arguments`（arguments 为 JSON 字符串）。

**`backend/app/services/llm/openai_compatible.py`**
- `supports_tools = True`。
- 实现 `complete_with_tools`：`chat.completions.create(..., tools=tools)`；解析 `response.choices[0].message`，把 `tool_calls`（id/function.name/function.arguments）与 `content` 装入 `AgentToolResponse`；两者皆空抛 `LLMServiceError`。错误处理复用 `_raise_provider_error`。

### 2. 只读回复工具注册表（新文件）

**`backend/app/agent/reply_tools.py`**（新建）
- `ReplyTool` dataclass：`name / description / parameters(JSON Schema) / handler`。
- `ReplyToolRegistry`：
  - 构造注入：`policy_repository`、`policy_search_tool`（复用 main.py 已装配的 Dify/Rag 工具）、`RuleEligibilityTool(repository)`（新建实例，确定性）、`OfficialRealtimePolicySearchTool`（复用 main.py 装配实例）、realtime enabled 标志、`InMemorySessionStore`（读材料声明）。
  - `definitions() -> list[dict]`：OpenAI tools JSON Schema。
  - `async execute(name, arguments_json) -> str`：JSON 结果字符串；单工具异常捕获并返回错误 JSON（不让工具错误中断循环）。
- 工具清单（全部只读）：
  | 工具 | 作用 | 后端复用 |
  |---|---|---|
  | `search_policies(query)` | 按需重新检索本地已核验政策 | `policy_search_tool.search(state.userProfile, query)`（见 rag_policy.py:L26） |
  | `get_policy_detail(policy_id)` | 取单条政策完整结构化记录 | `PolicyRepository.get_by_id` |
  | `check_eligibility(policy_id)` | 对指定政策做确定性资格核验 | `RuleEligibilityTool.check`（rule_eligibility.py:L50） |
  | `check_materials(policy_id)` | 查该政策材料要求与当前声明状态 | `MaterialCheckTool._requirements` + store 声明（material_check.py:L35） |
  | `search_realtime_policy(query, reason)` | 实时官方检索（未启用时返回 DISABLED 说明） | `OfficialRealtimePolicySearchTool.search`（tool.py:L27），沿用域名 allowlist |

### 3. Agent 回复引擎（新文件）

**`backend/app/services/agent_reply_engine.py`**（新建）
- `AgentReplyEngine(provider, registry, *, timeout_seconds=15, max_tool_rounds=3)`。
- `async generate(request, state, history) -> AgentReplyOutcome(reply, tool_rounds, grounded)`：
  1. **场景化策略指令**（`_strategy_directive(state)`）：按 `queryMode/domainIntent/needFollowUp/candidatePolicies/overallPlan/realtimeSearchStatus` 生成对应回复策略段落，例如：
     - FACT_QUERY 无画像 → 直接给政策事实 + 官方来源，结尾自然引导补充画像；
     - FOLLOW_UP → 围绕 followUpQuestions 自然追问，一次不超过两个问题，不复读模板；
     - PASS + plan → 结论先行，概括资格结论、关键材料和办理步骤；
     - NO_POLICY → 如实说明未命中 + 引导补充地区/毕业/就业信息；
     - REALTIME_STATUS_ONLY → 只引用 realtimePolicyHits 的标题/URL，不越界下资格结论。
  2. **有界工具循环**：`provider.supports_tools` 时，≤`max_tool_rounds` 轮调用 `complete_with_tools`；有 `tool_calls` 就执行 registry 并把 assistant(tool_calls) + tool 结果追加进 messages；拿到 `content` 即进入校验。不支持 tools 的 provider → 单次 `complete()`（兼容旧 Fake 与降级）。
  3. **Grounding 校验**（替代/吸收 `_may_use_llm_reply` 语义）：
     - 允许提及的政策名/ID 集合 = `state.candidatePolicies` + `state.knowledgeEvidences` + `state.realtimePolicyHits`（title/relatedPolicyId）+ 本轮工具结果返回的政策（registry 记录每轮工具产出的 policyId/name）；
     - 用正则 `《(.+?)》` 扫回复中提到的政策名，及已知 policyId 字面量；出现集合之外的 → `grounded=False`；
     - 沿用旧硬规则：`policyReferenceNotices` 非空、或无候选且无工具结果却出现"补贴/见习/贷款/创业社会保险"等推荐话术且 `needFollowUp` → 拒绝（保留 `test_follow_up_guard_rejects_llm_policy_recommendations` 的行为）。
  4. 整体 `asyncio.wait_for(timeout_seconds)` 包裹；任何异常向上抛由 ChatService 捕获回退。

### 4. ChatService 接入

**`backend/app/services/chat_service.py`**
- 构造函数新增可选参数 `reply_engine: AgentReplyEngine | None = None`。
- 新增/调整判定：`FinalExplanationPolicy` 保留不动（其 skip_reason 仍写日志）；新增决策（可放在 engine 模块内 `AgentReplyPolicy.decide(state)`）：**OUT_OF_SCOPE / MATERIAL_UPDATE / HISTORICAL_ONLY 保持确定性快速路径（不调 LLM，测试锁定该行为），其余场景一律走 agent 引擎**。
- `chat()`：engine 可用且决策通过 → `reply = engine.generate(...)`，异常/超时/`grounded=False` → 现有 `_fallback_reply(state, decision)`；成功后仍追加 `_realtime_reply` 的实时提示段（保持现有行为）。legacy 非 tools provider 的单次 `complete()` 路径收敛进 engine（`_may_use_llm_reply` 逻辑移入 grounding 校验，行为等价）。
- `stream_chat()`：
  - engine 路径：循环跑完得到完整回复 → 以**单个 delta 事件** yield 全文 → `done`（前端拼接 delta 的逻辑天然兼容）；
  - 非 tools provider → 保持现有 `provider.stream()` 逐块 delta 行为不变；
  - 异常 → 无 delta、`done` 携带模板回复（不变）。
- `_log_request_timing`：保留全部现有字段（`test_response_latency_policy` 逐字段断言），**追加** `agent_reply_rounds=%d agent_reply_ms=%d`。

### 5. 配置

**`backend/app/core/config.py`**：新增
- `agent_reply_enabled: bool = True`
- `agent_reply_max_tool_rounds: int = 3`
- `agent_reply_timeout_seconds: float = 15.0`
- `from_env()` 对应读取；`enabled=False` 时引擎完全不装配，行为与当前版本一致。

**`backend/.env.example` 与 `backend/.env`**：追加上述三个变量（带中文注释）。

### 6. 装配

**`backend/app/main.py`**（L149-156 附近）：
- `ReplyToolRegistry(policy_repository, policy_search_tool, realtime_tool, realtime_enabled=..., store=store)`；
- `AgentReplyEngine(active_provider, registry, timeout_seconds=..., max_tool_rounds=...)`（仅 `settings.agent_reply_enabled and settings.llm_configured` 时创建）；
- 传入 `ChatService(..., reply_engine=engine)`。

### 7. 测试

**新增 `backend/tests/test_agent_reply.py`**：
- `ToolCallingProvider`（`supports_tools=True`，脚本化：第 1 次返回 `tool_calls: search_policies`，第 2 次返回引用检索结果的回复）：
  - 断言工具被执行、`replyText` == LLM 回复、`ChatData` 结构不变；
  - grounding 违例：Fake 直接回复提到不在集合内的政策名 → `replyText` 回退模板；
  - provider 抛错 → 模板回退、HTTP 200、结构完整；
  - 轮次上限：Fake 永远返回 tool_calls → 3 轮后回退模板；
  - `agent_reply_enabled=False` → 不调用 provider。
**更新 `backend/tests/test_response_latency_policy.py`**：
- OUT_OF_SCOPE / HISTORICAL / NO_POLICY / MATERIAL_UPDATE 仍断言 `complete_calls == 0`（不变）；
- FOLLOW_UP 场景从"跳过"改为"调用 1 次"（SpyProvider 走 engine 的 legacy 单次路径）；
- normal + comparison 各 1 次不变；timeout 测试语义不变（engine 超时 → 模板回退）。
- `test_release_regression.py` / `test_chat_api.py`：Fake 均无 `supports_tools`，走等价 legacy 路径，**预期全部原样通过**（执行时验证，若有断言差异按"行为等价"原则修正）。

## 关键复用

- 政策检索：`RagPolicySearchTool.search` / `DifyPolicySearchTool`（main.py 已装配）
- 资格核验：`RuleEligibilityTool.check`（确定性，唯一 PASS/FAIL 来源）
- 实时检索：`OfficialRealtimePolicySearchTool.search`（allowlist/防注入已内建）
- 会话历史：`InMemorySessionStore.get_messages`（engine 直接复用 `_messages()` 的历史段）
- 模板回退：`ChatService._fallback_reply` 全套保留

## 验证

1. `cd backend && .venv\Scripts\python.exe -m pytest --basetemp="$env:USERPROFILE\qincheng-pytest-tmp"` — 全量通过（含新增 test_agent_reply.py）。
2. 启动后端（已配置真实 LLM Key）+ 前端，浏览器实测：
   - 「我符合创业社会保险补贴吗？」（画像不足）→ 回复应为自然追问而非模板句"已完成初步政策分析…"；
   - 「创业社会保险补贴需要什么条件？」→ FACT_QUERY 场景自然语言政策事实；
   - 「周末哪里看电影？」→ 仍秒回 OUT_OF_SCOPE 固定话术（确定性快速路径）；
   - 「我已经准备好《苏州市创业社会保险补贴申请表》」→ MATERIAL_UPDATE 确认话术不变；
   - 观察后端日志 `agent_reply_rounds` 与 `agent_request_timing` 新字段。
3. 前端 `npm run typecheck && npm run build` 确认零改动可编译（前端不改）。
