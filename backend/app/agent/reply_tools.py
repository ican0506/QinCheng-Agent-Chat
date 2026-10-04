from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Awaitable, Callable

from app.agent.models import PolicyCandidate
from app.agent.tools.material_check import MaterialCheckTool
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.models.chat import UserProfile
from app.policy.models import ApplicationStatus, ValidityStatus
from app.policy.repository import PolicyRepository
from app.realtime_policy.models import RealtimePolicyHit
from app.realtime_policy.provider import DisabledRealtimeSearchProvider
from app.realtime_policy.tool import OfficialRealtimePolicySearchTool


@dataclass
class ReplyToolContext:
    """一次 Agent 回复内共享的只读上下文；allowed 集合用于回复事实接地校验。"""

    profile: UserProfile
    material_declarations: dict[str, bool] = field(default_factory=dict)
    allowed_policy_ids: set[str] = field(default_factory=set)
    allowed_policy_names: set[str] = field(default_factory=set)
    tool_result_texts: list[str] = field(default_factory=list)
    web_search_results: list[dict[str, str]] = field(default_factory=list)


Handler = Callable[[dict[str, Any], ReplyToolContext], Awaitable[Any]]


@dataclass(frozen=True)
class ReplyTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


class ReplyToolRegistry:
    """面向 Agent 回复的只读工具注册表。

    所有工具只读取已核验政策库与用户声明，不修改任何会话状态；
    工具返回过的政策会进入 context.allowed_*，供回复接地校验使用。
    """

    def __init__(
        self,
        policy_repository: PolicyRepository,
        policy_search_tool,
        realtime_tool: OfficialRealtimePolicySearchTool,
        *,
        realtime_enabled: bool,
        eligibility_tool: RuleEligibilityTool | None = None,
        current_date: date | None = None,
        web_search_tool=None,
    ) -> None:
        self._repository = policy_repository
        self._policy_search_tool = policy_search_tool
        self._realtime_tool = realtime_tool
        self._realtime_enabled = realtime_enabled
        self._web_search_tool = web_search_tool
        self._eligibility_tool = eligibility_tool or RuleEligibilityTool(
            policy_repository, as_of_date=current_date
        )
        self._tools: dict[str, ReplyTool] = {
            tool.name: tool for tool in self._build_tools()
        }

    # ------------------------------------------------------------------ tools

    def _build_tools(self) -> list[ReplyTool]:
        return [
            ReplyTool(
                name="search_policies",
                description="在本地已核验政策库中按需求检索政策，返回政策名称、条件、材料与官方来源。当结构化上下文不足以回答用户问题时调用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索关键词或自然语言问题，例如“创业社会保险补贴 申报条件”",
                        },
                    },
                    "required": ["query"],
                },
                handler=self._run_search_policies,
            ),
            ReplyTool(
                name="get_policy_detail",
                description="按 policyId 获取单条已核验政策的完整结构化记录：全部条件、材料、办理流程、时效与申报窗口状态。",
                parameters={
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string", "description": "政策ID，例如 suzhou-startup-social-2021"},
                    },
                    "required": ["policy_id"],
                },
                handler=self._run_get_policy_detail,
            ),
            ReplyTool(
                name="check_eligibility",
                description="按 policyId 对当前用户画像执行确定性资格规则核验，返回 PASS/FAIL/UNKNOWN/MANUAL_REVIEW 及逐条原因。资格结论只能来自该工具或结构化上下文。",
                parameters={
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string", "description": "政策ID"},
                    },
                    "required": ["policy_id"],
                },
                handler=self._run_check_eligibility,
            ),
            ReplyTool(
                name="check_materials",
                description="按 policyId 查询该政策的材料要求与用户当前的材料声明状态。",
                parameters={
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string", "description": "政策ID"},
                    },
                    "required": ["policy_id"],
                },
                handler=self._run_check_materials,
            ),
            ReplyTool(
                name="search_realtime_policy",
                description="检索官方域名（苏州市政府/人社局）的最新公开政策与申报通知。仅在用户询问最新政策、当前申报状态或历史官方通知时调用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "官方检索查询词"},
                        "reason": {"type": "string", "description": "触发原因，例如“用户询问当前是否仍可申报”"},
                    },
                    "required": ["query", "reason"],
                },
                handler=self._run_search_realtime,
            ),
            ReplyTool(
                name="search_web",
                description=(
                    "用户已开启联网搜索：检索全网最新公开信息。当需要最新政策动态、时效性信息或本地政策库没有的事实时调用；"
                    "引用结果必须附来源标题与 URL。检索词必须包含当前年份以定位最新内容（当前日期见系统提示）；"
                    "用户询问「最近/最新/今年」类信息时必须传 time_range 参数。"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "联网检索查询词，建议包含当前年份，例如“苏州 毕业生 创业补贴 2026年 最新”"},
                        "time_range": {
                            "type": "string",
                            "enum": ["week", "month", "year"],
                            "description": "时间范围过滤：week=最近一周，month=最近一月，year=最近一年。查询时效性信息时必传。",
                        },
                    },
                    "required": ["query"],
                },
                handler=self._run_search_web,
            ),
        ]

    # --------------------------------------------------------------- registry

    def definitions(self, web_search: bool = False) -> list[dict[str, Any]]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
            if tool.name != "search_web" or web_search
        ]
        return tools

    async def execute(self, name: str, arguments: str, context: ReplyToolContext) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return _json({"error": f"未知工具：{name}"})
        try:
            args = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return _json({"error": "工具参数不是合法 JSON"})
        try:
            result = await tool.handler(args, context)
        except Exception as exc:  # 工具异常不中断 Agent 循环
            result: Any = {"error": f"工具执行失败：{type(exc).__name__}"}
            text = _json(result)
            context.tool_result_texts.append(text)
            return text
        text = _json(result)
        context.tool_result_texts.append(text)
        return text

    # ---------------------------------------------------------------- handlers

    @staticmethod
    def _remember(context: ReplyToolContext, *candidates: PolicyCandidate | None) -> None:
        for candidate in candidates:
            if candidate is None:
                continue
            context.allowed_policy_ids.add(candidate.policyId)
            context.allowed_policy_names.add(candidate.name)

    async def _run_search_policies(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"error": "缺少 query 参数"}
        candidates = await self._policy_search_tool.search(context.profile, query)
        self._remember(context, *candidates)
        return {
            "query": query,
            "policies": [candidate.model_dump(mode="json") for candidate in candidates],
        }

    async def _run_get_policy_detail(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        policy_id = str(args.get("policy_id") or "").strip()
        record = self._repository.get_by_id(policy_id) if policy_id else None
        if record is None:
            return {"error": f"政策库中不存在 policyId={policy_id or '<空>'} 的记录"}
        candidate = self._candidate_from_record(record)
        self._remember(context, candidate)
        return {
            "policyId": record.policyId,
            "name": record.name,
            "region": record.region,
            "department": record.department,
            "summary": record.summary,
            "conditions": [condition.description for condition in record.conditions],
            "requiredMaterials": record.requiredMaterials,
            "process": record.process,
            "validityStatus": record.validityStatus.value,
            "applicationStatus": record.applicationStatus.value,
            "sourceUrl": record.sourceUrl,
        }

    async def _run_check_eligibility(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        policy_id = str(args.get("policy_id") or "").strip()
        record = self._repository.get_by_id(policy_id) if policy_id else None
        if record is None:
            return {"error": f"政策库中不存在 policyId={policy_id or '<空>'} 的记录"}
        candidate = self._candidate_from_record(record)
        self._remember(context, candidate)
        results = await self._eligibility_tool.check(context.profile, [candidate])
        return {
            "policyId": policy_id,
            "eligibility": [result.model_dump(mode="json") for result in results],
        }

    async def _run_check_materials(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        policy_id = str(args.get("policy_id") or "").strip()
        record = self._repository.get_by_id(policy_id) if policy_id else None
        if record is None:
            return {"error": f"政策库中不存在 policyId={policy_id or '<空>'} 的记录"}
        candidate = self._candidate_from_record(record)
        self._remember(context, candidate)
        materials = []
        for name in record.requiredMaterials:
            if not MaterialCheckTool.is_concrete_material(name):
                materials.append({"materialName": name, "status": "MANUAL_REVIEW",
                                  "reason": "具体材料以经办渠道当前要求为准"})
                continue
            material_id = MaterialCheckTool.material_id(record.policyId, name)
            declared = context.material_declarations.get(material_id)
            status = "READY" if declared is True else "MISSING" if declared is False else "UNKNOWN"
            materials.append({
                "materialId": material_id,
                "materialName": name,
                "status": status,
                "reason": "用户已声明准备好" if declared is True
                else "用户已声明尚未准备" if declared is False
                else "尚未收到用户对该材料准备情况的明确说明",
            })
        historical = record.validityStatus in {ValidityStatus.HISTORICAL, ValidityStatus.EXPIRED}
        closed = record.applicationStatus is ApplicationStatus.CLOSED
        return {
            "policyId": record.policyId,
            "materials": materials,
            "validityStatus": record.validityStatus.value,
            "applicationStatus": record.applicationStatus.value,
            "notice": "该记录为历史/关闭状态，材料仅作历史参考。" if historical or closed else None,
        }

    async def _run_search_realtime(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        query = str(args.get("query") or "").strip()
        reason = str(args.get("reason") or "Agent 回复需要实时官方证据").strip()
        if not query:
            return {"error": "缺少 query 参数"}
        if not self._realtime_enabled or isinstance(self._realtime_tool.provider, DisabledRealtimeSearchProvider):
            return {"status": "DISABLED", "note": "实时官方检索未启用，只能使用本地已核验政策库。"}
        status, hits = await self._realtime_tool.search(context.profile, query, reason)
        self._remember_realtime(context, hits)
        return {
            "status": status.value,
            "hits": [
                {
                    "title": hit.title,
                    "url": hit.url,
                    "publishedAt": hit.publishedAt.isoformat() if hit.publishedAt else None,
                    "snippet": hit.snippet,
                    "relatedPolicyId": hit.relatedPolicyId,
                    "official": True,
                }
                for hit in hits
            ],
        }

    async def _run_search_web(self, args: dict[str, Any], context: ReplyToolContext) -> Any:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"status": "ERROR", "note": "缺少 query 参数", "results": []}
        if self._web_search_tool is None:
            return {"status": "DISABLED", "note": "联网搜索服务未配置，只能基于本地已核验信息回答。", "results": []}
        time_range = str(args.get("time_range") or "").strip() or None
        result = await self._web_search_tool.search(query, time_range=time_range)
        if result.get("status") == "OK":
            context.web_search_results.extend(result.get("results", []))
        return result

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _remember_realtime(context: ReplyToolContext, hits: list[RealtimePolicyHit]) -> None:
        for hit in hits:
            if hit.relatedPolicyId:
                context.allowed_policy_ids.add(hit.relatedPolicyId)
                record_hint = hit.title
                if record_hint:
                    context.allowed_policy_names.add(record_hint)

    @staticmethod
    def _candidate_from_record(record) -> PolicyCandidate:
        return PolicyCandidate(
            policyId=record.policyId,
            name=record.name,
            region=record.region,
            department=record.department,
            summary=record.summary,
            effectiveDate=record.effectiveDate or "",
            expiryDate=record.expiryDate,
            sourceUrl=record.sourceUrl or "",
            matchReason="Agent 回复期间按 policyId 直接调取已核验政策记录",
            conditions=[condition.description for condition in record.conditions],
            requiredMaterials=record.requiredMaterials,
            process=record.process,
            isMock=False,
        )
