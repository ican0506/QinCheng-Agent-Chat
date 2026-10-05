from __future__ import annotations

from pathlib import Path
import asyncio

from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.models import GovernmentAgentState, PolicyCandidate
from app.agent.target_policy import TargetPolicyResolver
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.mock import MockPlanTool, MockPolicyCompareTool
from app.agent.tools.rule_eligibility import RuleEligibilityTool
from app.agent.workflow import WorkflowAgent
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.services.policy_query_context import GoalResolver, UserGoal


def _candidate(policy_id: str, name: str) -> PolicyCandidate:
    return PolicyCandidate(
        policyId=policy_id, name=name, region="苏州市", department="苏州市人社局",
        summary="测试", effectiveDate="", sourceUrl="https://www.suzhou.gov.cn/test", matchReason="测试", isMock=False,
    )


def test_goal_resolver_classifies_fact_guide_and_active_policy_short_reply() -> None:
    assert GoalResolver.resolve("一次性创业补贴有多少钱") is UserGoal.POLICY_FACT
    assert GoalResolver.resolve("去哪里申请") is UserGoal.APPLICATION_GUIDE
    assert GoalResolver.resolve("那我可以吗", UserGoal.POLICY_FACT) is UserGoal.ELIGIBILITY_CHECK
    assert GoalResolver.resolve("需要准备什么材料", UserGoal.POLICY_FACT) is UserGoal.APPLICATION_GUIDE
    assert GoalResolver.resolve("我不想创业，只想就业") is UserGoal.JOB_SEARCH


def test_target_policy_resolver_locks_explicit_policy() -> None:
    repo = PolicyRepository(Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json")
    resolver = TargetPolicyResolver(repo)
    assert resolver.resolve("创业社会保险补贴需要什么条件") == "suzhou-startup-social-2021"


def _agent(repo: PolicyRepository) -> WorkflowAgent:
    return WorkflowAgent(
        ProfileNode(),
        PolicySearchNode(LocalPolicySearchTool(repo), repo),
        EligibilityNode(RuleEligibilityTool(repo)),
        PolicyCompareNode(MockPolicyCompareTool()),
        PlanNode(MockPlanTool()),
        repository=repo,
    )


def test_target_policy_stays_locked_across_fact_eligibility_and_material_turns() -> None:
    repo = PolicyRepository(Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json")
    agent = _agent(repo)
    profile = UserProfile(city="苏州市")

    fact = asyncio.run(agent.run("target-flow", "创业社会保险补贴需要什么条件", profile))
    assert fact.userGoal is UserGoal.POLICY_FACT
    assert fact.targetPolicyId == "suzhou-startup-social-2021"
    assert fact.activePolicy == fact.targetPolicyId

    eligibility = asyncio.run(agent.run(
        "target-flow", "那我可以吗", profile,
        active_goal=fact.activeGoal, active_policy=fact.activePolicy,
    ))
    assert eligibility.userGoal is UserGoal.ELIGIBILITY_CHECK
    assert eligibility.targetPolicyId == "suzhou-startup-social-2021"
    assert [policy.policyId for policy in eligibility.candidatePolicies] == ["suzhou-startup-social-2021"]
    assert eligibility.eligibilityResults
    assert {result.policyId for result in eligibility.eligibilityResults} == {"suzhou-startup-social-2021"}

    materials = asyncio.run(agent.run(
        "target-flow", "需要准备什么材料", profile,
        active_goal=eligibility.activeGoal, active_policy=eligibility.activePolicy,
    ))
    assert materials.userGoal is UserGoal.APPLICATION_GUIDE
    assert materials.targetPolicyId == "suzhou-startup-social-2021"
    assert [policy.policyId for policy in materials.candidatePolicies] == ["suzhou-startup-social-2021"]


def test_target_policy_isolated_between_sessions() -> None:
    repo = PolicyRepository(Path(__file__).resolve().parents[1] / "data" / "policies" / "policies.json")
    agent = _agent(repo)
    profile = UserProfile(city="苏州市")
    left = asyncio.run(agent.run("session-a", "创业社会保险补贴需要什么条件", profile))
    right = asyncio.run(agent.run("session-b", "就业见习适合哪些毕业生", profile))
    resumed_right = asyncio.run(agent.run(
        "session-b", "那我可以吗", profile,
        active_goal=right.activeGoal, active_policy=right.activePolicy,
    ))

    assert left.activePolicy == "suzhou-startup-social-2021"
    assert right.activePolicy == "suzhou-employment-internship-2024"
    assert resumed_right.targetPolicyId == "suzhou-employment-internship-2024"
    assert [policy.policyId for policy in resumed_right.candidatePolicies] == ["suzhou-employment-internship-2024"]


def test_fact_presentation_only_shows_the_explicit_target_policy() -> None:
    target = _candidate("suzhou-startup-social-2021", "创业社会保险补贴")
    other = _candidate("suzhou-startup-one-time-2023", "一次性创业补贴")
    state = GovernmentAgentState(
        sessionId="target-presentation", userMessage="创业社会保险补贴需要什么条件", userProfile=UserProfile(),
        userGoal=UserGoal.POLICY_FACT, activePolicy=target.policyId, targetPolicyId=target.policyId,
        candidatePolicies=[target, other],
    )

    from app.agent.presentation import PresentationAdapter
    reply = PresentationAdapter.fallback_reply(state)

    assert "创业社会保险补贴" in reply
    assert "一次性创业补贴" not in reply
