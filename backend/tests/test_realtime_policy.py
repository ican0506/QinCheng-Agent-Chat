import asyncio
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.realtime_policy.intent import FreshnessIntentDetector
from app.realtime_policy.models import SearchResult, RealtimeSearchStatus
from app.realtime_policy.provider import FakeRealtimeSearchProvider
from app.realtime_policy.security import canonical_url
from app.realtime_policy.tool import OfficialRealtimePolicySearchTool
from app.agent.nodes.realtime_policy_search import RealtimePolicySearchNode
from app.agent.models import GovernmentAgentState
from app.models.chat import UserProfile
from app.policy.repository import PolicyRepository
from app.main import create_app
from test_real_workflow_tools import settings, payload, parse_sse
from test_release_regression import FailingProvider, MisleadingProvider

ROOT = Path(__file__).resolve().parents[1] / 'data/policies'

@pytest.mark.parametrize('message', ['最新', '现在', '当前', '今年', '目前', '还能申请吗', '还能申领吗', '窗口开了吗', '什么时候截止', '申报时间', '最新通知', '新政策', '最近发布', '2026年最新', '2025届求职创业补贴当时什么时候申报？'])
def test_freshness(message):
    assert FreshnessIntentDetector.detect(message).requiresRealtimeSearch

def test_regular_question():
    assert not FreshnessIntentDetector.detect('创业社会保险补贴需要什么条件？').requiresRealtimeSearch

@pytest.mark.parametrize('url,allowed', [('https://hrss.suzhou.gov.cn/a', True), ('https://www.suzhou.gov.cn/a', True), ('https://hrss.suzhou.gov.cn.fake.com/a', False), ('https://suzhou.gov.cn.evil.com/a', False), ('http://suzhou.gov.cn/a', False), ('https://localhost/a', False), ('https://127.0.0.1/a', False), ('file:///a', False)])
def test_domains(url, allowed):
    assert bool(canonical_url(url, ['suzhou.gov.cn'])) is allowed

def test_canonical_keeps_query():
    assert canonical_url('https://WWW.SUZHOU.GOV.CN:443/a?x=1#part', ['suzhou.gov.cn']) == 'https://www.suzhou.gov.cn/a?x=1'

def node(provider, enabled=True, timeout=1):
    repo = PolicyRepository(ROOT / 'policies.json')
    tool = OfficialRealtimePolicySearchTool(provider, repo, ['suzhou.gov.cn'], timeout_seconds=timeout)
    return RealtimePolicySearchNode(tool, enabled=enabled), repo

def run(node, message='创业补贴现在还能申请吗？'):
    return asyncio.run(node.execute(GovernmentAgentState(sessionId='realtime-test', userMessage=message, userProfile=UserProfile(city='苏州市'))))

def test_disabled_and_not_triggered_do_not_call():
    provider = FakeRealtimeSearchProvider([])
    n, _ = node(provider, False)
    assert run(n).realtimeSearchStatus == RealtimeSearchStatus.DISABLED
    n, _ = node(provider)
    assert run(n, '创业社会保险补贴需要什么条件？').realtimeSearchStatus == RealtimeSearchStatus.NOT_TRIGGERED
    assert provider.call_count == 0

def test_deduplicate_associate_and_read_only():
    repo = PolicyRepository(ROOT / 'policies.json')
    record = repo.filter()[0]
    before = (ROOT / 'policies.json').read_bytes()
    provider = FakeRealtimeSearchProvider([SearchResult(title=record.name, url=record.sourceUrl, snippet='官方摘要'), SearchResult(title=record.name, url=record.sourceUrl + '#a', snippet='重复'), SearchResult(title='新官方通知', url='https://www.suzhou.gov.cn/new', snippet='新通知'), SearchResult(title='伪造', url='https://suzhou.gov.cn.evil.com/a', snippet='')])
    n, _ = node(provider)
    state = run(n)
    assert state.realtimeSearchStatus == RealtimeSearchStatus.SUCCESS
    assert len(state.realtimePolicyHits) == 2
    assert next(h for h in state.realtimePolicyHits if h.title == record.name).relatedPolicyId == record.policyId
    assert next(h for h in state.realtimePolicyHits if h.title == '新官方通知').relatedPolicyId is None
    assert state.candidatePolicies == state.eligibilityResults == state.materialResults == []
    assert state.overallPlan is None
    assert provider.call_count == 1
    assert (ROOT / 'policies.json').read_bytes() == before

@pytest.mark.parametrize('provider,status', [(FakeRealtimeSearchProvider([]), RealtimeSearchStatus.NO_RESULTS), (FakeRealtimeSearchProvider([], error=RuntimeError('failed')), RealtimeSearchStatus.ERROR), (FakeRealtimeSearchProvider([], delay=0.02), RealtimeSearchStatus.TIMEOUT)])
def test_result_status(provider, status):
    n, _ = node(provider, timeout=0.001)
    assert run(n).realtimeSearchStatus == status

@pytest.mark.parametrize('llm', [FailingProvider(), MisleadingProvider()])
def test_api_sse_evidence_and_eligibility_isolation(llm):
    from dataclasses import replace
    provider = FakeRealtimeSearchProvider([SearchResult(title='全新官方补贴通知', url='https://www.suzhou.gov.cn/new-notice', snippet='通知内容', publishedAt=date(2026, 9, 30))])
    app = create_app(replace(settings(), realtime_policy_search_enabled=True), llm, realtime_provider=provider)
    client = TestClient(app)
    request = payload('创业社会保险补贴现在还能申请吗？', {'graduationDate':'2025-06-20', 'socialInsuranceMonths':12, 'businessRegistrationMonths':12})
    data = client.post('/api/agent/chat', json=request).json()['data']
    assert '全新官方补贴通知' in data['replyText']
    assert 'https://www.suzhou.gov.cn/new-notice' in data['replyText']
    assert '尚未完成结构化核验' in data['replyText']
    assert all(p['name'] != '全新官方补贴通知' for p in data['policies'])
    baseline = TestClient(create_app(settings(), FailingProvider())).post('/api/agent/chat', json=request).json()['data']
    for field in ['policies','eligibility','materialResults','plan']:
        assert data[field] == baseline[field]
    events = parse_sse(client.post('/api/agent/chat/stream', json=request).text)
    assert events[-1][0] == 'done'
    assert set(events[-1][1]['data']) == set(data)
    assert '尚未完成结构化核验' in events[-1][1]['data']['replyText']

@pytest.mark.parametrize('provider,status,notice', [(FakeRealtimeSearchProvider([]), RealtimeSearchStatus.NO_RESULTS, '已完成实时查询'), (FakeRealtimeSearchProvider([], error=RuntimeError()), RealtimeSearchStatus.ERROR, '暂时无法检索'), (FakeRealtimeSearchProvider([], delay=0.02), RealtimeSearchStatus.TIMEOUT, '暂时无法检索')])
def test_failure_and_empty_keep_entire_local_workflow(provider, status, notice):
    from dataclasses import replace
    request = payload('创业社会保险补贴现在还能申请吗？', {'graduationDate':'2025-06-20', 'socialInsuranceMonths':12, 'businessRegistrationMonths':12})
    cfg = replace(settings(), realtime_policy_search_enabled=True, realtime_policy_search_timeout_seconds=0.001)
    app = create_app(cfg, FailingProvider(), realtime_provider=provider)
    data = TestClient(app).post('/api/agent/chat', json=request).json()['data']
    assert notice in data['replyText']
    assert data['policies'] and data['eligibility'] and data['materialResults'] and data['plan']

def test_associated_evidence_keeps_repository_rules_and_materials():
    from dataclasses import replace
    repo = PolicyRepository(ROOT / 'policies.json')
    record = repo.get_by_id('suzhou-startup-social-2021')
    before = record.model_dump()
    provider = FakeRealtimeSearchProvider([SearchResult(title=record.name, url=record.sourceUrl, snippet='新网页声称所有人都符合')])
    request = payload('创业社会保险补贴现在还能申请吗？', {'graduationDate':'2025-06-20', 'socialInsuranceMonths':1, 'businessRegistrationMonths':12})
    app = create_app(replace(settings(), realtime_policy_search_enabled=True), MisleadingProvider(), realtime_provider=provider)
    data = TestClient(app).post('/api/agent/chat', json=request).json()['data']
    result = next(r for r in data['eligibility'] if r['policyId'] == record.policyId)
    assert result['overallStatus'] == 'FAIL'
    assert '所有人都符合' not in data['replyText']
    assert repo.get_by_id(record.policyId).model_dump() == before

def test_status_reply_and_prompt_have_explicit_boundaries():
    from app.services.chat_service import ChatService, SYSTEM_PROMPT
    notices = {}
    for status in [RealtimeSearchStatus.DISABLED, RealtimeSearchStatus.NO_RESULTS, RealtimeSearchStatus.TIMEOUT]:
        state = GovernmentAgentState(sessionId='status', userMessage='最新政策', userProfile=UserProfile(), realtimeSearchStatus=status)
        notices[status] = ChatService._fallback_reply(state)
    assert len(set(notices.values())) == 3
    assert '未配置实时检索服务' in notices[RealtimeSearchStatus.DISABLED]
    assert '不能说用户符合' in SYSTEM_PROMPT
