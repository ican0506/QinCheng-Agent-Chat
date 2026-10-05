from __future__ import annotations

import sys
from pathlib import Path

from app.agent.models import GovernmentAgentState
from app.models.chat import UserProfile
from app.services.policy_query_context import UserGoal


BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmark"
sys.path.insert(0, str(BENCHMARK_DIR))
from cases import benchmark_cases  # noqa: E402
from runner import BenchmarkTurn, _score  # noqa: E402


def test_c27_profile_statements_expect_profile_update_without_search() -> None:
    case = next(item for item in benchmark_cases() if item.case_id == "C27")

    assert [(turn.expected_goal, turn.expect_search) for turn in case.turns] == [
        (UserGoal.PROFILE_UPDATE, False),
        (UserGoal.PROFILE_UPDATE, False),
    ]


def test_job_search_scorer_rejects_historical_subsidy_only_reply() -> None:
    state = GovernmentAgentState(
        sessionId="benchmark-job", userMessage="我快毕业了，不知道去哪找工作", userProfile=UserProfile(),
        userGoal=UserGoal.JOB_SEARCH,
    )
    turn = BenchmarkTurn(state.userMessage, UserGoal.JOB_SEARCH, True)

    scores, issues = _score(turn, state, "当前历史补贴申报已结束，请关注后续通知。")

    assert scores["actionability"] < 2
    assert scores["retrievalRelevance"] < 2
    assert any("JOB_SEARCH" in item for item in issues)
