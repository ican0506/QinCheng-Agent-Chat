from __future__ import annotations

import asyncio

from app.agent.workflow import WorkflowAgent
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.tools.mock import MockEligibilityTool, MockPlanTool, MockPolicyCompareTool, MockPolicySearchTool
from app.models.chat import UserProfile
from app.services.policy_query_context import UserGoal


def test_policy_fact_graph_skips_eligibility_material_and_plan() -> None:
    state = asyncio.run(
        WorkflowAgent.default().run(
            session_id="graph-fact-session",
            message="创业社会保险补贴需要什么条件？",
            user_profile=UserProfile(city="苏州市"),
            user_goal=UserGoal.POLICY_FACT,
        )
    )

    assert state.candidatePolicies
    assert state.eligibilityResults == []
    assert state.materialResults == []
    assert state.overallPlan is None
    assert state.suggestedActions


def test_eligibility_graph_keeps_structured_rule_boundary() -> None:
    state = asyncio.run(
        WorkflowAgent.default().run(
            session_id="graph-eligibility-session",
            message="我符合创业补贴吗？",
            user_profile=UserProfile(city="苏州市"),
            user_goal=UserGoal.ELIGIBILITY_CHECK,
        )
    )

    assert state.candidatePolicies
    assert state.eligibilityResults
    assert state.needFollowUp is True
    assert 1 <= len(state.requiredFieldsForCurrentGoal) <= 2


def test_follow_up_goal_resumes_active_goal_inside_graph() -> None:
    state = asyncio.run(
        WorkflowAgent.default().run(
            session_id="graph-follow-up-session",
            message="有昆山市户籍",
            user_profile=UserProfile(city="苏州市", residencyRegistration="本市户籍"),
            user_goal=UserGoal.FOLLOW_UP_REPLY,
            active_goal=UserGoal.ELIGIBILITY_CHECK,
        )
    )

    assert state.userGoal is UserGoal.ELIGIBILITY_CHECK
    assert state.activeGoal is UserGoal.ELIGIBILITY_CHECK
    assert state.routeDecision.runEligibility is True


def test_policy_fact_runs_official_search_before_structured_fallback() -> None:
    calls: list[str] = []

    class RecordingSearch(MockPolicySearchTool):
        async def search(self, profile: UserProfile, message: str):
            calls.append("structured")
            return await super().search(profile, message)

    class RecordingOfficialSearch:
        async def execute(self, state, *, force: bool = False):
            assert force is True
            calls.append("official")
            return state

    agent = WorkflowAgent(
        ProfileNode(),
        PolicySearchNode(RecordingSearch()),
        EligibilityNode(MockEligibilityTool()),
        PolicyCompareNode(MockPolicyCompareTool()),
        PlanNode(MockPlanTool()),
        realtime_node=RecordingOfficialSearch(),
    )
    state = asyncio.run(
        agent.run(
            session_id="graph-web-first-session",
            message="创业社会保险补贴需要什么条件？",
            user_profile=UserProfile(city="苏州市"),
            user_goal=UserGoal.POLICY_FACT,
        )
    )

    assert calls == ["official", "structured"]
    assert state.eligibilityResults == []
