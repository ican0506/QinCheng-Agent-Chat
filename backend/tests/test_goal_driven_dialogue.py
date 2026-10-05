from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.policy_query_context import GoalResolver, RouteDecider, UserGoal
from test_real_workflow_tools import settings
from test_release_regression import FailingProvider


def client() -> TestClient:
    return TestClient(
        create_app(replace(settings(), profile_extraction_enabled=False), FailingProvider())
    )


def send(client: TestClient, message: str, session_id: str = "goal-dialogue-session") -> dict:
    response = client.post(
        "/api/agent/chat",
        json={
            "sessionId": session_id,
            "userId": "goal-dialogue-user",
            "message": message,
            "userProfile": {},
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_job_search_answers_first_without_eligibility_material_or_plan() -> None:
    data = send(
        client(),
        "我在苏州，本科，2026年6月20日毕业，目前未就业，只想找工作",
    )

    assert data["needFollowUp"] is False
    assert data["followUpQuestions"] == []
    assert data["eligibility"] == []
    assert data["materialResults"] == []
    assert data["plan"] is None
    assert "灵活就业方式参保" not in data["replyText"]
    assert "本市户籍" not in data["replyText"]
    assert data["suggestedActions"]


def test_policy_fact_returns_facts_without_eligibility_material_or_plan() -> None:
    data = send(client(), "创业社会保险补贴需要什么条件？")

    assert data["policies"]
    assert data["eligibility"] == []
    assert data["materialResults"] == []
    assert data["plan"] is None
    assert data["needFollowUp"] is False
    assert data["suggestedActions"]


def test_eligibility_check_only_asks_policy_specific_missing_fields() -> None:
    data = send(client(), "我符合创业社会保险补贴吗？")

    assert data["needFollowUp"] is True
    assert 1 <= len(data["followUpQuestions"]) <= 2
    assert data["eligibility"]
    assert "学历" not in "；".join(data["followUpQuestions"])


def test_explicit_job_search_replaces_previous_eligibility_goal() -> None:
    active_client = client()
    first = send(active_client, "我符合创业社会保险补贴吗？")
    assert first["needFollowUp"] is True

    data = send(active_client, "先不管补贴了，我只想找工作")
    assert data["needFollowUp"] is False
    assert data["eligibility"] == []
    assert data["materialResults"] == []
    assert data["plan"] is None
    assert "经营主体" not in data["replyText"]


def test_application_guide_returns_process_without_full_profile_gate() -> None:
    data = send(client(), "创业社会保险补贴怎么办理？")

    assert data["policies"]
    assert data["needFollowUp"] is False
    assert data["materialResults"] == []
    assert data["plan"] is None
    assert data["applicationGuide"] is True
    assert "办理流程" in data["replyText"]


def test_goal_resolver_and_route_decider_keep_routing_explicit() -> None:
    goal = GoalResolver.resolve("创业社会保险补贴怎么办理？")
    route = RouteDecider.decide(goal)

    assert goal is UserGoal.APPLICATION_GUIDE
    assert route.runPolicySearch is True
    assert route.runEligibility is False
    assert route.runMaterialCheck is False
    assert route.runPlan is False
    assert route.generateSuggestions is True


def test_follow_up_reply_continues_previous_goal() -> None:
    goal = GoalResolver.resolve("我已经连续缴纳社保12个月", UserGoal.ELIGIBILITY_CHECK)
    route = RouteDecider.decide(goal, previous_goal=UserGoal.ELIGIBILITY_CHECK)

    assert goal is UserGoal.FOLLOW_UP_REPLY
    assert route.needsProfileGate is True
    assert route.runEligibility is True


def test_goal_resolver_covers_fact_discovery_job_and_eligibility() -> None:
    assert GoalResolver.resolve("创业社会保险补贴需要什么条件？") is UserGoal.POLICY_FACT
    assert GoalResolver.resolve("毕业生现在有什么就业支持？") is UserGoal.POLICY_DISCOVERY
    assert GoalResolver.resolve("我只想找工作") is UserGoal.JOB_SEARCH
    assert GoalResolver.resolve("我符合创业社会保险补贴吗？") is UserGoal.ELIGIBILITY_CHECK


def test_next_step_and_profile_update_continue_the_session_goal() -> None:
    active_client = client()
    first = send(active_client, "我在苏州，本科，2026年毕业，目前待就业，只想找工作")
    assert first["suggestedActions"]

    next_step = send(active_client, "那下一步我该干什么？")
    assert next_step["suggestedActions"]
    assert next_step["eligibility"] == []

    changed = send(active_client, "我现在已经找到工作了")
    assert changed["userProfile"]["employmentStatus"] == "已就业"
    assert changed["eligibility"] == []


def test_session_goal_and_profile_are_isolated() -> None:
    active_client = client()
    left = send(active_client, "我在苏州，本科，2026年毕业，目前待就业，只想找工作", "goal-left")
    right = send(active_client, "我在苏州，准备创业", "goal-right")

    assert left["userProfile"]["education"] == "本科"
    assert right["userProfile"]["education"] is None
    assert right["eligibility"] == []
