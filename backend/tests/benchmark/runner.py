"""真实 Agent benchmark runner；运行时不打印或持久化任何密钥。"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from types import MethodType
from typing import Any

from fastapi.testclient import TestClient

from app.agent.models import GovernmentAgentState
from app.agent.realtime_relevance import relevant_realtime_hits
from app.main import create_app
from app.models.chat import UserProfile
from app.realtime_policy.models import RealtimeSearchStatus
from app.services.policy_query_context import UserGoal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases import BenchmarkCase, BenchmarkTurn, benchmark_cases

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CHECKPOINT_PATH = RESULTS_DIR / "checkpoint.jsonl"
RESULTS_PATH = RESULTS_DIR / "results.json"


@dataclass
class TurnResult:
    caseId: str
    category: str
    turn: int
    input: str
    expectedGoal: str
    resolvedGoal: str
    routeDecision: dict[str, bool]
    nodes: list[str]
    searched: bool
    searchQuery: str | None
    realtimeStatus: str
    evidence: list[dict[str, str]]
    policyIds: list[str]
    eligibilityStatuses: list[str]
    followUpQuestions: list[str]
    suggestedActions: list[str]
    finalReply: str
    workspace: dict[str, int | bool]
    totalMs: float
    scores: dict[str, int]
    issues: list[str]
    severity: list[str]


def _nodes(state: GovernmentAgentState) -> list[str]:
    nodes = ["resolve_goal"]
    if state.userGoal not in {UserGoal.CONVERSATIONAL, UserGoal.OUT_OF_SCOPE}:
        nodes.append("merge_profile")
    if state.routeDecision.runPolicySearch:
        if state.realtimeSearchStatus is not RealtimeSearchStatus.NOT_TRIGGERED:
            nodes.append("official_search")
        nodes.append("policy_search")
    if state.routeDecision.runEligibility:
        nodes.extend(["required_fields", "eligibility"])
    if state.routeDecision.runMaterialCheck:
        nodes.append("material")
    if state.routeDecision.runPlan:
        nodes.append("plan")
    return nodes + ["presentation"]


def _score(turn: BenchmarkTurn, state: GovernmentAgentState, reply: str) -> tuple[dict[str, int], list[str]]:
    issues: list[str] = []
    goal = 2 if state.userGoal is turn.expected_goal else 0
    if not goal:
        issues.append(f"目标误判：期望 {turn.expected_goal.value}，实际 {state.userGoal.value}")
    searched = state.routeDecision.runPolicySearch
    retrieval = 2 if searched is turn.expect_search else 0
    if not retrieval:
        issues.append("检索边界不符合预期")
    displayed_hits = relevant_realtime_hits(state)
    urls = [hit.url for hit in displayed_hits] + [item.sourceUrl for item in state.knowledgeEvidences]
    official = 2 if (not urls or all(url.startswith("https://") and ("suzhou.gov.cn" in url or "hrss.suzhou.gov.cn" in url) for url in urls)) else 0
    if not official:
        issues.append("出现非官方或非 HTTPS 证据")
    historical_query = "历史" in turn.message or "2026届求职创业补贴" in turn.message
    freshness = 2 if not historical_query or ("历史" in reply and ("结束" in reply or "不能" in reply)) else 0
    if not freshness:
        issues.append("历史政策时效提示不足")
    profile_empty = not any(getattr(state.userProfile, field, None) for field in ("city", "education", "graduationYear", "employmentStatus"))
    personalization = 0 if profile_empty and "根据你" in reply else 2
    if not personalization:
        issues.append("无画像时出现个性化断言")
    clarification = 2 if len(state.followUpQuestions) <= 2 else 0
    if not clarification:
        issues.append("追问超过两个字段")
    if state.userGoal is UserGoal.JOB_SEARCH:
        employment_words = ("就业", "招聘", "岗位", "见习", "求职", "就业服务")
        action_words = ("下一步", "查看", "查询", "参加", "对接", "联系")
        startup_words = ("创业补贴", "创业社会保险补贴", "一次性创业补贴")
        historical_only = ("历史" in reply or "已结束" in reply) and not any(word in reply for word in employment_words)
        relevant_evidence = bool(displayed_hits) and all(
            any(word in f"{hit.title} {hit.snippet}" for word in employment_words)
            for hit in displayed_hits
        )
        if not relevant_evidence or historical_only:
            retrieval = 0
            issues.append("JOB_SEARCH 未展示相关就业证据")
        actionability = 2 if any(word in reply for word in employment_words) and any(word in reply for word in action_words) and not any(word in reply for word in startup_words) else 0
        if not actionability:
            issues.append("JOB_SEARCH 缺少就业行动方向或错误推荐创业政策")
    else:
        actionability = 2 if state.userGoal is UserGoal.CONVERSATIONAL or state.suggestedActions or any(word in reply for word in ("办理", "申请", "关注", "下一步")) else 1
    internal = ("Dify", "RAG", "Tavily", "chunk", "embedding", "UserGoal", "QueryMode")
    quality = 2 if reply and not any(word in reply for word in internal) else 0
    if not quality:
        issues.append("回复为空或泄露内部术语")
    # 对金额的保守检测：数字出现但不在后端 State 中时，标记为可能幻觉。
    state_text = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
    grounding = 2
    if re.search(r"\d+\s*元", reply) and not re.search(r"\d+\s*元", state_text):
        grounding = 0
        issues.append("可能编造金额")
    return {
        "goalAccuracy": goal, "retrievalRelevance": retrieval, "officialSourceQuality": official,
        "freshness": freshness, "grounding": grounding, "personalization": personalization,
        "clarificationEfficiency": clarification, "actionability": actionability, "responseQuality": quality,
    }, issues


def _report(results: list[TurnResult], path: Path) -> None:
    if not results:
        path.write_text("# 青程 Agent 真实场景 Benchmark 报告\n\n尚无已完成 case。\n", encoding="utf-8")
        return
    total = len(results) * 18
    got = sum(sum(item.scores.values()) for item in results)
    metrics = {key: sum(item.scores[key] for item in results) / (2 * len(results)) for key in results[0].scores}
    p0 = [item for item in results if "P0" in item.severity]
    p1 = [item for item in results if "P1" in item.severity]
    lines = ["# 青程 Agent 真实场景 Benchmark 报告", "", "## 总体得分", "", f"- 总分：{got}/{total}（{got / total:.1%}）", f"- 评测轮数：{len(results)}", f"- Goal Accuracy：{metrics['goalAccuracy']:.1%}", f"- Retrieval Precision：{metrics['retrievalRelevance']:.1%}", f"- 官方来源占比：{metrics['officialSourceQuality']:.1%}", f"- 平均响应时间：{sum(item.totalMs for item in results) / len(results):.0f} ms", f"- P0：{len(p0)}；P1：{len(p1)}", "", "## Case 明细", ""]
    for item in results:
        lines.extend((f"### {item.caseId} / Turn {item.turn}：{item.category}", "", f"- 输入：{item.input}", f"- Goal：{item.resolvedGoal}（期望 {item.expectedGoal}）", f"- 节点：{' → '.join(item.nodes)}", f"- 搜索：{item.searched}；实时状态：{item.realtimeStatus}", f"- 政策：{', '.join(item.policyIds) or '无'}", f"- 追问：{'；'.join(item.followUpQuestions) or '无'}", f"- 回复：{item.finalReply}", f"- 得分：{sum(item.scores.values())}/18", f"- 严重级别：{', '.join(item.severity) or '无'}", f"- 问题：{'；'.join(item.issues) or '无'}", ""))
    lines.extend(("## 优化优先级", "", "- P0：先处理任何金额/资格无证据断言或跨会话画像泄露。", "- P1：处理目标误判、检索边界和历史政策时效提示。", "- P2：优化建议动作的针对性、回复简洁度和响应时延。", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def _severity(issues: list[str]) -> list[str]:
    levels: list[str] = []
    if any("编造" in item or "无画像" in item for item in issues):
        levels.append("P0")
    if any(key in item for item in issues for key in ("目标误判", "检索边界", "时效", "非官方")):
        levels.append("P1")
    return levels


def load_checkpoint(path: Path = CHECKPOINT_PATH) -> dict[str, list[TurnResult]]:
    if not path.exists():
        return {}
    completed: dict[str, list[TurnResult]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        case_id = item["caseId"]
        # 只接受整组完成记录，避免多轮会话被半组跳过。
        completed[case_id] = [TurnResult(**turn) for turn in item["turns"]]
    return completed


def append_checkpoint(case: BenchmarkCase, turns: list[TurnResult], path: Path = CHECKPOINT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"caseId": case.case_id, "turns": [asdict(turn) for turn in turns]}, ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(payload + "\n")
        handle.flush()
        __import__("os").fsync(handle.fileno())


def _case_aliases(cases: tuple[BenchmarkCase, ...]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    counts: dict[str, int] = {}
    for case in cases:
        prefix = case.category.split("：", 1)[0].lower().replace(" ", "_")
        prefix = {"普通会话": "conversation", "多轮": "multi_turn"}.get(prefix, prefix)
        counts[prefix] = counts.get(prefix, 0) + 1
        aliases[f"{prefix}_{counts[prefix]:02d}"] = case.case_id
    aliases.update({"job_search_01": "C05", "policy_fact_01": "C13"})
    return aliases


def select_cases(*, start: int = 0, limit: int | None = None, case_id: str | None = None, resume: bool = False) -> tuple[BenchmarkCase, ...]:
    cases = benchmark_cases()
    if case_id:
        target = _case_aliases(cases).get(case_id.lower(), case_id.upper())
        return tuple(item for item in cases if item.case_id == target)
    selected = cases[start:] if limit is None else cases[start:start + limit]
    if resume:
        completed = load_checkpoint()
        selected = tuple(item for item in selected if item.case_id not in completed)
    return tuple(selected)


def run(cases: tuple[BenchmarkCase, ...], *, checkpoint_path: Path = CHECKPOINT_PATH) -> list[TurnResult]:
    app = create_app()
    workflow = app.state.workflow_agent
    original_run = workflow.run
    captured: list[GovernmentAgentState] = []

    async def recording_run(self, *args: Any, **kwargs: Any) -> GovernmentAgentState:
        state = await original_run(*args, **kwargs)
        captured.append(state)
        return state

    workflow.run = MethodType(recording_run, workflow)
    results: list[TurnResult] = []
    with TestClient(app) as client:
        for case in cases:
            session_id = f"benchmark-{case.case_id.lower()}"
            case_turns: list[TurnResult] = []
            for index, turn in enumerate(case.turns, start=1):
                started = time.perf_counter()
                capture_count = len(captured)
                try:
                    response = client.post("/api/agent/chat", json={
                        "sessionId": session_id, "userId": "benchmark-user", "message": turn.message, "userProfile": {},
                    })
                    elapsed = (time.perf_counter() - started) * 1000
                    response.raise_for_status()
                    data = response.json()["data"]
                    state = captured[-1]
                    scores, issues = _score(turn, state, data["replyText"])
                except Exception as exc:  # 外部联网/模型波动应计入结果，不能中断整个评测。
                    elapsed = (time.perf_counter() - started) * 1000
                    state = captured[-1] if len(captured) > capture_count else GovernmentAgentState(
                        sessionId=session_id, userMessage=turn.message, userProfile=UserProfile(),
                    )
                    data = {"replyText": "", "policies": [], "eligibility": [], "materialResults": [], "plan": None}
                    scores = {key: 0 for key in ("goalAccuracy", "retrievalRelevance", "officialSourceQuality", "freshness", "grounding", "personalization", "clarificationEfficiency", "actionability", "responseQuality")}
                    issues = [f"Benchmark 请求异常：{type(exc).__name__}"]
                evidence = [{"title": hit.title, "url": hit.url} for hit in state.realtimePolicyHits]
                evidence.extend({"title": item.policyName, "url": item.sourceUrl} for item in state.knowledgeEvidences)
                case_turns.append(TurnResult(
                    case.case_id, case.category, index, turn.message, turn.expected_goal.value, state.userGoal.value,
                    state.routeDecision.model_dump(), _nodes(state), state.routeDecision.runPolicySearch,
                    state.policySearchQuery, state.realtimeSearchStatus.value, evidence,
                    [item.policyId for item in state.candidatePolicies], [item.overallStatus.value for item in state.eligibilityResults],
                    list(state.followUpQuestions), [item.label for item in state.suggestedActions], data["replyText"],
                    {"policies": len(data["policies"]), "eligibility": len(data["eligibility"]), "materials": len(data["materialResults"]), "hasPlan": bool(data["plan"])}, elapsed, scores, issues, _severity(issues),
                ))
            append_checkpoint(case, case_turns, checkpoint_path)
            results.extend(case_turns)
    return results


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.ERROR)
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--report", default="../../../docs/agent-benchmark-report.md")
    parser.add_argument("--json", default=str(RESULTS_PATH))
    args = parser.parse_args()
    report_path = (ROOT / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        completed = load_checkpoint()
        output = [turn for turns in completed.values() for turn in turns]
    else:
        output = run(select_cases(start=args.start, limit=args.limit, case_id=args.case, resume=args.resume))
        completed = load_checkpoint()
        output = [turn for turns in completed.values() for turn in turns]
    _report(output, report_path)
    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps([asdict(item) for item in output], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"benchmark completed_cases={len(load_checkpoint())} turns={len(output)} report={report_path}")
