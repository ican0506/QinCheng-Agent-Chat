# 高校毕业生就业创业政策智能 Agent

面向高校毕业生就业、创业场景的政策信息检索、资格辅助判断与办理路径规划项目。后端提供普通 Chat 与 SSE 流式接口；前端提供 Vue 3 对话界面。

本项目不是政府部门审批系统。最终资格、申报材料、办理时间和审批结果以相关政府部门最新官方规定及实际审核为准。

## 当前能力

- 用户画像采用 LLM 结构化信息抽取，并通过 Pydantic/确定性规则进行字段校验和归一化；模型不可用时回退到本地规则解析器；
- 苏州市高校毕业生就业创业政策检索；
- 已核验官方政策原文知识库检索与来源追溯；
- 确定性资格辅助判断：`PASS`、`FAIL`、`UNKNOWN`、`MANUAL_REVIEW`；
- 确定性政策关系分析与办理路径规划；
- 官方结构化材料清单与轻量材料准备状态预检；
- OpenAI-compatible LLM 仅负责画像信息抽取和语言组织解释；
- `POST /api/agent/chat` 与 `POST /api/agent/chat/stream`。

## 当前 Workflow

```text
User Message
    ↓
ProfileNode
    ↓
RagPolicySearchTool
    ↓
RuleEligibilityTool
    ↓
PolicyCompareTool
    ↓
MaterialCheckTool
    ↓
PlanTool
    ↓
LLM Explanation
    ↓
Chat API / SSE
```

- `RagPolicySearchTool`：召回政策、检索原文片段并提供官方来源依据；知识库异常时回退到 `LocalPolicySearchTool`。
- `RuleEligibilityTool`：唯一负责确定性资格判断，LLM 不决定资格结论。
- `PolicyCompareTool`：只读取显式、可追溯的关系配置，不根据名称、主题或人群猜测政策间关系。
- `PlanTool`：根据资格结果、政策时效、申报窗口、缺失信息、材料和显式关系生成结构化办理步骤。
- `MaterialCheckTool`：只读取已核验政策记录中的具体材料，并依据用户明确陈述标记材料准备状态；不识别文件、不判断真伪。
- LLM：只负责结构化画像信息抽取和基于 Agent State 的最终中文说明；资格判断仍由 RuleEligibilityTool 完成。

## 政策数据范围

当前仅覆盖苏州市高校毕业生就业创业场景的 5 条已核验政策记录，包括一次性创业补贴、创业社会保险补贴、灵活就业社会保险补贴、就业见习与求职创业补贴历史通知。

来源为苏州市政府官网、苏州市人力资源和社会保障局等官方页面。数据保存在：

```text
backend/data/policies/policies.json
backend/data/policies/raw/*.md
backend/data/policies/policy_relations.json
```

`policy_relations.json` 当前为空数组：现有 5 条政策没有足够官方依据支持 `MUTEX` 或 `PREREQUISITE`，项目不会为了演示制造关系。

## 本地政策原文检索

知识库只使用已核验的本地 Markdown 政策原文，并能将每个命中片段追溯到政策 ID、官方 `sourceUrl`、时效状态和最后核验日期。

检索过程：

```text
Markdown 二级标题优先切分
    ↓
Metadata Filter（地区 / 主题 / 目标人群 / 时效状态）
    ↓
中文字符 2/3-gram TF-IDF
    ↓
余弦相关性排序 + Top-K + 最低相关度阈值
    ↓
PolicyCandidate 去重
```

这是轻量本地文本相关性检索，不是 embedding、深度语义模型或外部向量数据库。

## 资格辅助判断

`RuleEligibilityTool` 是确定性规则引擎，支持：

```text
eq / gte / lte / in / not_in / exists / within_years
```

结果语义：

- `PASS`：当前结构化信息明确满足；
- `FAIL`：当前结构化信息明确不满足；
- `UNKNOWN`：缺少必要信息，会转为有限的补充问题；
- `MANUAL_REVIEW`：需要材料或经办机构人工确认。

LLM 不参与最终资格判断，也不覆盖上述状态。

## 政策关系与办理路径

`PolicyCompareTool` 支持 `PREREQUISITE`、`PARALLEL`、`MUTEX`、`TIME_DEPENDENT`，但只输出显式配置且有政策依据的关系。

`PlanTool` 使用以下结构化动作生成稳定步骤：

```text
PROVIDE_INFO
VERIFY_ELIGIBILITY
PREPARE_MATERIALS
MANUAL_REVIEW
APPLY_POLICY
WAIT_FOR_WINDOW
NOTICE
```

计划不会自动审批：`FAIL`、历史或失效政策不会进入申请主路径；窗口关闭的政策会生成等待窗口提示；相同缺失字段只会生成一条统一补充信息步骤。

## 技术栈

- Frontend：Vue 3、TypeScript、Vite
- Backend：FastAPI、Pydantic、WorkflowAgent
- Policy：PolicyRepository、PolicyRecord、PolicyCondition
- Retrieval：RagPolicySearchTool、中文字符 n-gram TF-IDF、LocalPolicySearchTool fallback
- Eligibility：RuleEligibilityTool
- Planning：PolicyCompareTool、PlanTool
- LLM：OpenAI-compatible provider

## 本地启动

### 后端

```powershell
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Git Bash：

```bash
source .venv/Scripts/activate
```

安装并启动：

```powershell
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

- 服务地址：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

如需真实 LLM 调用，复制 `backend/.env.example` 为 `.env`，并按现有环境变量配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。`PROFILE_EXTRACTION_ENABLED=true` 时启用 LLM 结构化画像抽取并在失败时回退规则解析；设为 `false` 时仅使用规则解析。不要提交 `.env` 或真实 API Key。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

开发地址默认为 `http://localhost:5173`。

## 测试

```powershell
cd backend
pytest

cd ../frontend
npm run typecheck
npm run build
```

比赛演示输入与预期结果见 [docs/COMPETITION_SCENARIOS.md](docs/COMPETITION_SCENARIOS.md)，发布前检查见 [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)。

## 当前限制

- 当前政策库仅有 5 条真实苏州市政策，不覆盖全国或完整苏州市全部政策；
- 当前主要覆盖高校毕业生就业创业场景；
- 本地原文检索不是 embedding 模型；
- 部分政策条件需要 `MANUAL_REVIEW`；
- 部分政策的 `applicationStatus` 仍为 `UNKNOWN`；
- 部分政策的官方材料和流程信息不完整；
- 当前不支持 OCR、文件上传、材料真伪校验或自动审批；材料完整性取决于已核验的结构化政策记录；
- 前端 Workspace 由每个会话最近一次 SSE `done.data` 的真实 `ChatData` 驱动，展示后端返回的政策、资格辅助判断、补充问题、办理计划与官方来源；
- 尚未实现 OCR、文件上传、材料识别、Dify、外部向量数据库和业务数据库持久化。
