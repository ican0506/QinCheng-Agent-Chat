from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.rag.models import RagChunk
from app.rag.retriever import InMemoryRagRetriever
from app.services.profile_update_parser import ProfileUpdateParser
from test_real_workflow_tools import settings, parse_sse
from test_release_regression import FailingProvider


@pytest.mark.parametrize('message', [
    '我不创业', '我不是创业', '不是创业', '不创业', '不是要创业',
    '我不是要创业', '没有创业打算', '暂时不考虑创业', '只想找工作',
    '就是想找工作', '我不是创业，我只是自己交社保',
])
def test_deterministic_negative_intent(message):
    assert ProfileUpdateParser.deterministic_intent_overrides(message)['entrepreneurshipIntent'] is False


@pytest.mark.parametrize('message', ['创业政策有哪些', '创业补贴怎么领', '不是创业补贴的话还有什么政策'])
def test_policy_question_is_not_personal_negative_intent(message):
    assert 'entrepreneurshipIntent' not in ProfileUpdateParser.deterministic_intent_overrides(message)


@pytest.mark.parametrize('message', [
    '灵活就业交社保', '按灵活就业交社保', '自己按灵活就业交社保',
    '灵活就业缴社保', '灵活就业参保', '以灵活就业身份参保',
])
def test_flexible_insurance_declaration(message):
    assert ProfileUpdateParser.parse(message)['flexibleEmploymentInsurance'] is True


@pytest.mark.parametrize('message', ['灵活就业社保补贴是什么', '灵活就业交社保能申请什么补贴', '我没有灵活就业参保'])
def test_flexible_insurance_question_or_denial_is_not_positive(message):
    assert ProfileUpdateParser.parse(message).get('flexibleEmploymentInsurance') is not True


def client():
    return TestClient(create_app(replace(settings(), profile_extraction_enabled=False), FailingProvider()))


def send(c, message, session='intent-context-test', profile=None, stream=False):
    response = c.post('/api/agent/chat/stream' if stream else '/api/agent/chat', json={
        'sessionId': session, 'userId': 'intent-context-user', 'message': message,
        'userProfile': profile or {},
    })
    assert response.status_code == 200
    if stream:
        events = parse_sse(response.text)
        assert events[-1][0] == 'done'
        assert all(event == 'delta' for event, _ in events[:-1])
        return events[-1][1]['data']
    return response.json()['data']


def base_profile():
    return {'city': '苏州市', 'education': '本科', 'graduationYear': 2025, 'employmentStatus': '待就业'}


def store(c):
    return c.app.state.chat_service._store


def context(c, session='intent-context-test'):
    return asyncio.run(store(c).get_policy_query_context(session, 'intent-context-user'))


def test_browser_negative_intent_refreshes_candidates_materials_plan_and_follow_up():
    c = client()
    send(c, '我不是创业，我只是自己交社保')
    data = send(c, '我在苏州，本科，2025年6月20日毕业，目前待业，不创业，自己按灵活就业交社保', stream=True)
    profile = asyncio.run(store(c).get_internal_profile('intent-context-test', 'intent-context-user'))
    assert profile.entrepreneurshipIntent is False
    assert profile.flexibleEmploymentInsurance is True
    ids = {p['policyId'] for p in data['policies']}
    assert 'suzhou-flexible-social-2021' in ids
    assert not ids & {'suzhou-startup-social-2021', 'suzhou-startup-one-time-2023'}
    assert all(m['policyId'] in ids for m in data['materialResults'])
    assert not any('经营主体' in q or '首次创业' in q or '灵活就业方式参保' in q for q in data['followUpQuestions'])
    assert data['plan'] is None


def test_explicit_rules_override_conflicting_llm_and_historical_intent():
    c = client()
    send(c, '准备创业', profile=base_profile())
    class ConflictingExtractor:
        async def extract(self, message, stored_profile):
            return {'entrepreneurshipIntent': True, 'flexibleEmploymentInsurance': False}
    c.app.state.chat_service._profile_extractor = ConflictingExtractor()
    data = send(c, '不创业，自己按灵活就业交社保')
    profile = asyncio.run(store(c).get_internal_profile('intent-context-test', 'intent-context-user'))
    assert profile.entrepreneurshipIntent is False
    assert profile.flexibleEmploymentInsurance is True
    assert all(p['policyId'] != 'suzhou-startup-social-2021' for p in data['policies'])


def test_profile_only_correction_preserves_policy_query_context_and_results():
    c = client()
    first = send(c, '我想看看有什么就业补贴', profile=base_profile())
    assert first['policies']
    second = send(c, '之前说错了，其实我是硕士', stream=True)
    assert second['userProfile']['education'] == '硕士'
    assert second['userProfile']['city'] == '苏州市'
    # 首次只有画像补充而没有 active goal 时，修正画像不会凭空启动政策检索。
    assert second['policies']
    assert {p['policyId'] for p in first['policies']} == {p['policyId'] for p in second['policies']}
    assert '就业' in context(c)


def test_browser_implicit_consultation_survives_education_correction():
    c = client()
    send(c, '我去年本科毕业，目前待业，我在苏州')
    second = send(c, '之前说错了，其实我是硕士')
    assert second['policies'] == []
    assert second['userProfile']['graduationYear'] == date.today().year - 1


def test_new_topic_replaces_context_and_new_session_has_no_context():
    c = client()
    send(c, '我想了解就业补贴', profile=base_profile())
    send(c, '我不看就业了，我想了解创业补贴')
    assert '创业' in context(c)
    assert context(c, 'other-new-session') is None
    send(c, '其实我是硕士', session='other-new-session')
    assert '创业' not in (context(c, 'other-new-session') or '')


@pytest.mark.parametrize('message', ['换个问题', '重新开始', '周末哪里看电影？'])
def test_reset_or_unrelated_question_clears_previous_query_context(message):
    c = client()
    send(c, '我想了解创业补贴', profile=base_profile())
    send(c, message)
    assert context(c) is None


@pytest.mark.parametrize('message', ['周末哪里看电影？', '今天吃什么？', '给我讲个笑话'])
def test_out_of_scope_skips_entire_policy_chain_and_llm(message):
    c = client()
    async def forbidden(*args, **kwargs):
        raise AssertionError('OUT_OF_SCOPE 不得执行政策链')
    workflow = c.app.state.workflow_agent
    workflow._profile_node.execute = forbidden
    workflow._policy_search_node.execute = forbidden
    workflow._realtime_node.execute = forbidden
    workflow._eligibility_node.execute = forbidden
    c.app.state.chat_service._provider.complete = forbidden
    class ForbiddenExtractor:
        async def extract(self, *args):
            raise AssertionError('无关问题不得进行画像抽取')
    c.app.state.chat_service._profile_extractor = ForbiddenExtractor()
    data = send(c, message, stream=True)
    assert data['policies'] == data['eligibility'] == data['materialResults'] == []
    assert data['plan'] is None
    assert data['needFollowUp'] is False
    assert data['followUpQuestions'] == []
    assert '高校毕业生就业创业政策咨询' in data['replyText']


def test_out_of_scope_does_not_trigger_enabled_realtime_provider():
    from app.realtime_policy.provider import FakeRealtimeSearchProvider
    provider = FakeRealtimeSearchProvider([])
    c = TestClient(create_app(replace(settings(), realtime_policy_search_enabled=True), FailingProvider(), realtime_provider=provider))
    data = send(c, '现在周末哪里看电影？')
    assert provider.call_count == 0
    assert data['needFollowUp'] is False
    assert '未配置实时检索服务' not in data['replyText']


@pytest.mark.parametrize('message', ['补贴', '社保', '找工作'])
def test_short_uncertain_policy_query_is_not_out_of_scope(message):
    c = client()
    data = send(c, message)
    # 没有会话上下文的短语只能作为发现/求职意图，不能凭空进入资格问卷。
    assert data['needFollowUp'] is False
    assert data['eligibility'] == []


@pytest.mark.parametrize('message, expected', [
    ('我是2026届本科毕业生，现在有什么还能申请的补贴？', 'CURRENT'),
    ('2026届现在还能申请吗', 'CURRENT'),
    ('我去年毕业，想了解补贴', 'CURRENT'),
    ('我想看2025届当时的求职创业补贴通知', 'HISTORICAL'),
    ('之前的通知', 'HISTORICAL'), ('往年的申报时间', 'HISTORICAL'),
    ('去年的通知', 'HISTORICAL'), ('历史政策', 'HISTORICAL'),
    ('2025年当时什么时候截止', 'HISTORICAL'),
])
def test_query_temporal_intent(message, expected):
    from app.services.policy_query_context import QueryTemporalIntentDetector
    assert QueryTemporalIntentDetector.detect(message).value == expected


def test_current_policy_rank_is_a_status_bucket_not_small_score_adjustment():
    active = RagChunk(policyId='active', policyName='政策', region='苏州市', department='人社',
        sourceUrl='https://www.suzhou.gov.cn/a', validityStatus='ACTIVE', lastVerifiedAt=date.today(),
        topics=(), targetGroups=(), chunkId='a', heading='条件', chunkText='毕业生补贴 社保创业')
    historical = replace(active, policyId='old', chunkId='old', validityStatus='HISTORICAL',
        chunkText='求职补贴 求职补贴 求职补贴')
    unknown = replace(active, policyId='unknown', chunkId='u', validityStatus='UNKNOWN')
    index = InMemoryRagRetriever([historical, unknown, active])
    hits = index.search('求职补贴', top_k=3)
    assert [h.policyId for h in hits] == ['active', 'unknown', 'old']
    assert index.search('求职补贴', include_historical=True, top_k=3)[0].policyId == 'old'


def test_closed_active_record_ranks_after_open_current_record():
    from app.rag.loader import RagDocumentLoader
    from app.rag.chunker import MarkdownPolicyChunker
    from test_policy_rag import repository
    from pathlib import Path
    docs = RagDocumentLoader(repository(), Path(__file__).resolve().parents[1] / 'data/policies/raw').load()
    chunks = MarkdownPolicyChunker().chunk_documents(docs)
    assert all(hasattr(chunk, 'applicationStatus') for chunk in chunks)
    template = chunks[0]
    open_chunk = replace(template, policyId='open', chunkId='open', validityStatus='ACTIVE', applicationStatus='OPEN', chunkText='毕业生补贴')
    closed = replace(open_chunk, policyId='closed', chunkId='closed', applicationStatus='CLOSED')
    assert [h.policyId for h in InMemoryRagRetriever([closed, open_chunk]).search('毕业生补贴', top_k=2)] == ['open', 'closed']


def test_current_query_keeps_active_first_and_follow_up_with_scoped_history_notice():
    c = client()
    data = send(c, '我是2026届本科毕业生，现在在苏州还没就业，有什么现在还能申请的补贴？', profile=base_profile(), stream=True)
    repo = c.app.state.policy_repository
    statuses = [repo.get_by_id(p['policyId']).validityStatus.value for p in data['policies']]
    assert 'ACTIVE' in statuses and 'HISTORICAL' in statuses
    assert statuses.index('ACTIVE') < statuses.index('HISTORICAL')
    # “我现在还能申请”是在询问本人可申请性，应走范围受限的资格判断。
    assert data['needFollowUp'] is True
    assert len(data['followUpQuestions']) <= 2
    # 混合结果的历史状态保留在政策卡片，不追加到当前对话正文。
    assert '历史申报通知' not in data['replyText']
    assert '未配置实时检索服务' in data['replyText']


def test_explicit_historical_query_still_returns_history_and_correct_window_notice():
    c = client()
    data = send(c, '我想看2026届求职创业补贴之前的申报通知', profile=base_profile())
    assert data['policies'][0]['policyId'] == 'suzhou-job-seeking-subsidy-2026'
    assert '申报窗口已结束' in data['replyText']
    assert '后续发布的2025届' not in data['replyText']
