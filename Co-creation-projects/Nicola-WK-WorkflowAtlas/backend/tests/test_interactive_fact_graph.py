"""Explicit interactive graph conversion with synthetic model output only."""
import json

import pytest

from app.extraction.fact_graph import FactGraphAnalyzer, parse_fact_graph
from app.schemas import DirectModelAnswer
from test_direct_processing import direct_provider, graph_records, run_direct, seed_local_graph
from test_holistic_processing import forbid_semantic_rules, synthetic_report
from test_model_diagram_api import ANSWER, save_answer, setup_answer
from test_scoped_model_jobs import OTHER, TARGET


@pytest.fixture
def fact_provider(monkeypatch):
    from app.extraction import fact_graph, remote
    monkeypatch.setattr(remote, 'test_model_connection', lambda *args: {'ok': True, 'detail': 'Synthetic', 'latency_ms': 0})
    state = {'calls': [], 'callback': None, 'invalid': False}

    class FakeGraph:
        def __init__(self, settings):
            self.settings = settings

        def analyze(self, messages, markdown, *, cancel_check=None, on_delta=None):
            state['calls'].append((messages, markdown))
            on_delta('{"synthetic":true}')
            if state['callback']:
                state['callback']()
            report = synthetic_report(messages)
            report.tables = []
            if state.get('cross_project'):
                report.steps[1].workstream_id = report.workstreams[1].id
            if state['invalid']:
                report.steps[0].evidence[0].quote = 'Invented unsupported evidence'
            return report, DirectModelAnswer(markdown='{"synthetic":true}', model=self.settings.llm_model,
                         usage={'prompt_tokens': 80, 'completion_tokens': 40, 'total_tokens': 120})

    monkeypatch.setattr(fact_graph, 'FactGraphAnalyzer', FakeGraph)
    return state


def generate(client, source=TARGET):
    response = client.post('/api/model/facts', params={'source_id': source})
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued['purpose'] == 'facts'
    return client.get('/api/jobs/' + queued['id']).json()


def test_explicit_conversion_populates_interactive_graph_and_keeps_answer(client, fact_provider, monkeypatch):
    seed_local_graph(client)
    from test_model_settings import enable_remote
    enable_remote(client)
    save_answer(client)
    repository = client.app.state.repository
    before = repository.read_state('holistic_report:' + TARGET)
    retained = [f.model_dump() for f in repository.facts() if f.evidence[0].source_id == OTHER]
    forbid_semantic_rules(monkeypatch)
    assert client.get('/api/model/report', params={'source_id': TARGET}).json()['fact_graph'] is None
    assert fact_provider['calls'] == []
    job = generate(client)
    assert job['status'] == 'completed', job
    assert job['result']['facts'] == 3 and job['result']['projects'] == 2
    assert fact_provider['calls'][0][1] == ANSWER
    assert {m.source_id for m in fact_provider['calls'][0][0]} == {TARGET}
    assert repository.read_state('holistic_report:' + TARGET) == before
    assert [f.model_dump() for f in repository.facts() if f.evidence[0].source_id == OTHER] == retained
    projects = client.get('/api/projects', params={'source_id': TARGET}).json()
    assert len(projects) == 2
    project = next(p for p in projects if p['name'] == '模型综合归纳的交付主线')
    graph = client.get(f"/api/projects/{project['id']}/workflow", params={'source_id': TARGET}).json()
    assert len(graph['nodes']) == 2 and len(graph['edges']) == 1
    assert all(f['verified'] and f['review_status'] == 'pending' for f in graph['facts'])
    evidence = graph['facts'][0]['evidence'][0]
    original = client.get('/api/evidence', params={k: evidence[k] for k in ('source_id', 'message_id')}).json()
    assert evidence['quote'] in original['text']
    assert client.get('/api/export', params={'format': 'training', 'source_id': TARGET}).text == ''
    versions = client.get(f"/api/projects/{project['id']}/versions").json()
    assert versions[0]['version'] == job['result']['version']
    assert generate(client)['status'] == 'completed'
    assert len(fact_provider['calls']) == 1
    assert client.get('/api/model/report', params={'source_id': TARGET}).json()['fact_graph']['cached']


@pytest.mark.parametrize('failure', ['invalid', 'answer_changed', 'messages_changed', 'cancel', 'database'])
def test_failed_conversion_preserves_existing_graph(client, fact_provider, failure):
    seed_local_graph(client)
    from test_model_settings import enable_remote
    enable_remote(client)
    save_answer(client)
    before = graph_records(client)
    repository = client.app.state.repository
    if failure == 'invalid':
        fact_provider['invalid'] = True
    elif failure == 'answer_changed':
        fact_provider['callback'] = lambda: save_answer(client, ANSWER + '\nChanged answer')
    elif failure == 'messages_changed':
        from test_scoped_model_jobs import add_messages
        fact_provider['callback'] = lambda: add_messages(client, TARGET, 1, prefix='changed')
    elif failure == 'cancel':
        def cancel():
            job = next(j for j in repository.jobs() if j.status == 'running')
            client.app.state.processing.cancel(job.id)
        fact_provider['callback'] = cancel
    else:
        repository.connection.execute("CREATE TRIGGER fail_fact_graph BEFORE UPDATE ON jobs WHEN json_extract(NEW.payload,'$.status')='completed' AND json_extract(NEW.payload,'$.purpose')='facts' BEGIN SELECT RAISE(ABORT,'synthetic commit failure'); END")
    job = generate(client)
    assert job['status'] == ('cancelled' if failure == 'cancel' else 'failed'), job
    assert graph_records(client) == before
    assert repository.read_state('fact_graph:' + TARGET) is None
    assert job['progress']['markdown']


def test_queued_source_and_answer_binding_prevents_model_call(client, fact_provider, monkeypatch):
    setup_answer(client)
    repository = client.app.state.repository
    monkeypatch.setattr(client.app.state.processing, 'run', lambda *args: None)
    queued = client.post('/api/model/facts', params={'source_id': TARGET}).json()
    save_answer(client, ANSWER + '\nChanged while queued')
    result = client.app.state.processing._run_fact_graph(queued['id'], TARGET)
    assert result.status == 'failed' and fact_provider['calls'] == []


def test_cross_project_relation_retains_assignment_context_and_complete_export(client, fact_provider):
    setup_answer(client)
    fact_provider['cross_project'] = True
    job = generate(client)
    assert job['status'] == 'completed', job
    projects = client.get('/api/projects', params={'source_id': TARGET}).json()
    assert len(projects) == 2
    for project in projects:
        view = client.get(f"/api/projects/{project['id']}/workflow", params={'source_id': TARGET}).json()
        assert len(view['nodes']) == len(view['related_nodes']) == 1
        assert view['nodes'][0]['project_id'] == project['id']
        assert view['related_nodes'][0]['project_id'] != project['id']
        assert len(view['related_edges']) == len(view['related_facts']) == 1
        assert view['edges'] == []
        node_ids = {n['id'] for n in view['nodes'] + view['related_nodes']}
        edge = view['related_edges'][0]
        assert {edge['source'], edge['target']} == node_ids and edge['relation'] == 'blocks'
        exported = client.get('/api/export', params={'format': 'json', 'project_id': project['id'], 'source_id': TARGET}).json()
        assert {n['id'] for n in exported['nodes']} == node_ids
        assert len(exported['projects']) == 2 and len(exported['edges']) == 1
        assert all(f['review_status'] == 'pending' for f in exported['facts'])


def test_recovered_output_is_saved_without_another_model_call(client, fact_provider):
    from app.services.processing import _fact_graph_cache_key
    setup_answer(client)
    repository = client.app.state.repository
    selected = [m for m in repository.messages() if m.source_id == TARGET]
    report = synthetic_report(selected)
    report.tables = []
    report.steps[1].workstream_id = report.workstreams[1].id
    answer = DirectModelAnswer(markdown='existing paid output', model='synthetic', usage={'total_tokens': 120})
    key = _fact_graph_cache_key(selected, ANSWER, client.app.state.models.effective())
    repository.write_state(key, {'source_id': TARGET, 'report': report.model_dump(mode='json'),
        'answer': answer.model_dump(mode='json'), 'recovered_from_job': 'synthetic-original-job'})
    job = generate(client)
    assert job['status'] == 'completed' and fact_provider['calls'] == []
    assert job['progress']['recovered_from_job'] == 'synthetic-original-job'
    assert job['progress']['usage'] == {'total_tokens': 120}
    assert repository.read_state('fact_graph:' + TARGET)['recovered_from_job'] == 'synthetic-original-job'


def test_staleness_and_deletion_are_source_scoped(client, fact_provider):
    setup_answer(client)
    generate(client)
    save_answer(client, ANSWER + '\nNew saved conclusion')
    assert client.get('/api/model/report', params={'source_id': TARGET}).json()['fact_graph']['stale']
    generate(client)
    assert len(fact_provider['calls']) == 2
    preview = client.get('/api/sources/delete-preview', params={'source_id': TARGET}).json()
    response = client.request('DELETE', '/api/sources', params={'source_id': TARGET}, json={
        'confirmation': TARGET, 'expected_messages': preview['messages'], 'expected_version': preview['version']})
    assert response.status_code == 200, response.text
    rows = client.app.state.repository.connection.execute("SELECT key FROM state WHERE key LIKE 'fact_graph:%' OR key LIKE 'fact_graph_cache:%'").fetchall()
    assert rows == []


def test_fast_answer_remains_independent_and_graph_requires_explicit_action(client, fact_provider, direct_provider):
    setup_answer(client)
    before = graph_records(client)
    assert run_direct(client)['status'] == 'completed'
    assert fact_provider['calls'] == [] and graph_records(client) == before
    assert len(direct_provider['calls']) == 1


def test_fact_graph_endpoint_checks_source_answer_and_active_jobs(client, fact_provider):
    assert client.post('/api/model/facts', params={'source_id': 'missing'}).status_code == 404
    from test_scoped_model_jobs import add_messages
    add_messages(client, TARGET, 1)
    assert client.post('/api/model/facts', params={'source_id': TARGET}).status_code == 403
    from test_model_settings import enable_remote
    enable_remote(client)
    assert client.post('/api/model/facts', params={'source_id': TARGET}).status_code == 400
    save_answer(client)
    client.app.state.processing.enqueue(TARGET)
    assert client.post('/api/model/facts', params={'source_id': TARGET}).status_code == 409
    assert fact_provider['calls'] == []


def compact_graph(messages):
    report = synthetic_report(messages).model_dump(mode='json')
    report['tables'] = []
    indexes = {m.id: n for n, m in enumerate(messages, 1)}
    for section in ('workstreams', 'steps', 'relations'):
        for item in report[section]:
            item['evidence'] = [{'message': indexes[e['message_id']], 'quote': e['quote']} for e in item['evidence']]
    return report


@pytest.mark.parametrize('wrapped', [False, True])
def test_graph_adapter_uses_one_call_and_resolves_exact_quotes(client, monkeypatch, fact_provider, wrapped):
    setup_answer(client)
    messages = [m for m in client.app.state.repository.messages() if m.source_id == TARGET]
    text = json.dumps(compact_graph(messages), ensure_ascii=False)
    if wrapped:
        text = '```json\n' + text + '\n```'
    calls = []

    class FakeDirect:
        def __init__(self, settings):
            pass
        def analyze(self, items, **kwargs):
            calls.append((items, kwargs))
            return DirectModelAnswer(markdown=text, model='synthetic')

    monkeypatch.setattr('app.extraction.fact_graph.DirectAnalyzer', FakeDirect)
    report, _ = FactGraphAnalyzer(client.app.state.models.effective()).analyze(messages, ANSWER)
    assert len(calls) == 1 and len(calls[0][0]) == 1
    assert ANSWER in calls[0][0][0].text and all(m.text in calls[0][0][0].text for m in messages)
    assert report.steps[0].evidence[0].message_id == messages[0].id


@pytest.mark.parametrize('bad', ['quote', 'message', 'bool', 'relation'])
def test_invalid_source_references_are_rejected(client, fact_provider, bad):
    setup_answer(client)
    messages = [m for m in client.app.state.repository.messages() if m.source_id == TARGET]
    value = compact_graph(messages)
    if bad == 'quote':
        value['steps'][0]['evidence'][0]['quote'] = 'Invented evidence'
    elif bad == 'relation':
        value['relations'][0]['target_step_id'] = 'missing-node'
    else:
        value['steps'][0]['evidence'][0]['message'] = True if bad == 'bool' else 9999
    with pytest.raises(ValueError):
        parse_fact_graph(json.dumps(value), messages)
