from __future__ import annotations

from dataclasses import dataclass, field

from app.services.policy_query_context import UserGoal


@dataclass(frozen=True)
class BenchmarkTurn:
    message: str
    expected_goal: UserGoal
    expect_search: bool


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    turns: tuple[BenchmarkTurn, ...]
    notes: str = ""


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    single = (
        ("C01", "普通会话", "你好", UserGoal.CONVERSATIONAL, False),
        ("C02", "普通会话", "谢谢", UserGoal.CONVERSATIONAL, False),
        ("C03", "普通会话", "你是谁", UserGoal.CONVERSATIONAL, False),
        ("C04", "普通会话", "我都没告诉你我的情况，你怎么知道的", UserGoal.CONVERSATIONAL, False),
        ("C05", "JOB_SEARCH", "我是2026届本科生，现在没工作，只想找工作", UserGoal.JOB_SEARCH, True),
        ("C06", "JOB_SEARCH", "我快毕业了，不知道去哪找工作", UserGoal.JOB_SEARCH, True),
        ("C07", "JOB_SEARCH", "我不想创业，只想就业", UserGoal.JOB_SEARCH, True),
        ("C08", "JOB_SEARCH", "苏州最近有什么适合毕业生的就业服务", UserGoal.JOB_SEARCH, True),
        ("C09", "POLICY_DISCOVERY", "苏州毕业生现在有什么就业支持", UserGoal.POLICY_DISCOVERY, True),
        ("C10", "POLICY_DISCOVERY", "我今年毕业，有什么政策可以看看", UserGoal.POLICY_DISCOVERY, True),
        ("C11", "POLICY_DISCOVERY", "未就业毕业生有哪些支持", UserGoal.POLICY_DISCOVERY, True),
        ("C12", "POLICY_DISCOVERY", "创业的话有什么政策", UserGoal.POLICY_DISCOVERY, True),
        ("C13", "POLICY_FACT", "创业社会保险补贴需要什么条件", UserGoal.POLICY_FACT, True),
        ("C14", "POLICY_FACT", "就业见习适合哪些毕业生", UserGoal.POLICY_FACT, True),
        ("C15", "POLICY_FACT", "一次性创业补贴有多少钱", UserGoal.POLICY_FACT, True),
        ("C16", "POLICY_FACT", "灵活就业社保补贴是什么", UserGoal.POLICY_FACT, True),
        ("C17", "ELIGIBILITY_CHECK", "我符合创业社会保险补贴吗", UserGoal.ELIGIBILITY_CHECK, True),
        ("C18", "ELIGIBILITY_CHECK", "我2026年6月毕业，现在未就业，我符合就业见习吗", UserGoal.ELIGIBILITY_CHECK, True),
        ("C19", "ELIGIBILITY_CHECK", "我是太仓户籍，可以申请吗", UserGoal.ELIGIBILITY_CHECK, True),
        ("C20", "ELIGIBILITY_CHECK", "我自己交社保，能申请灵活就业补贴吗", UserGoal.ELIGIBILITY_CHECK, True),
        ("C21", "APPLICATION_GUIDE", "创业社会保险补贴怎么办理", UserGoal.APPLICATION_GUIDE, True),
        ("C22", "APPLICATION_GUIDE", "就业见习怎么申请", UserGoal.APPLICATION_GUIDE, True),
        ("C23", "APPLICATION_GUIDE", "创业社会保险补贴需要准备什么材料", UserGoal.APPLICATION_GUIDE, True),
        ("C24", "APPLICATION_GUIDE", "创业社会保险补贴去哪里申请", UserGoal.APPLICATION_GUIDE, True),
    )
    cases = [BenchmarkCase(case_id, category, (BenchmarkTurn(message, goal, search),)) for case_id, category, message, goal, search in single]
    cases.extend((
        BenchmarkCase("C25", "多轮：资格续接", (
            BenchmarkTurn("我符合创业社会保险补贴吗", UserGoal.ELIGIBILITY_CHECK, True),
            BenchmarkTurn("有昆山市户籍", UserGoal.ELIGIBILITY_CHECK, True),
        )),
        BenchmarkCase("C26", "多轮：目标切换", (
            BenchmarkTurn("我符合创业社会保险补贴吗", UserGoal.ELIGIBILITY_CHECK, True),
            BenchmarkTurn("先不管补贴了，我只想找工作", UserGoal.JOB_SEARCH, True),
        )),
        BenchmarkCase("C27", "多轮：画像纠正", (
            BenchmarkTurn("我在苏州，本科，今年毕业，目前待就业", UserGoal.PROFILE_UPDATE, False),
            BenchmarkTurn("之前说错了，其实我是硕士", UserGoal.PROFILE_UPDATE, False),
        )),
        BenchmarkCase("C28", "多轮：短追问", (
            BenchmarkTurn("创业社会保险补贴需要什么条件", UserGoal.POLICY_FACT, True),
            BenchmarkTurn("那我可以吗", UserGoal.ELIGIBILITY_CHECK, True),
        )),
        BenchmarkCase("C29", "多轮：下一步", (
            BenchmarkTurn("我是2026届毕业生，现在有什么就业支持", UserGoal.POLICY_DISCOVERY, True),
            BenchmarkTurn("那下一步呢", UserGoal.POLICY_DISCOVERY, True),
        )),
        BenchmarkCase("C30", "多轮：历史后致谢", (
            BenchmarkTurn("2026届求职创业补贴什么时候申报", UserGoal.POLICY_FACT, True),
            BenchmarkTurn("谢谢", UserGoal.CONVERSATIONAL, False),
        )),
    ))
    return tuple(cases)
