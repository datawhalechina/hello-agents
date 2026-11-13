"""Reproduce a model that keeps choosing reads until the client changes tools."""
import copy
import json
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from backend.analysis_context import AnalysisContext, ReadCapacityError
from backend.analysis_documents import ANALYSIS_SKILL, OUTPUT_PATHS
from backend.app import create_app
from backend.model import ActionFormatError, HelloModel, action_tool, documentation_action
from backend.workspace import Workspace


GRAPH = {'title': '模块关系', 'description': '入口使用工具模块处理任务。',
         'nodes': [{'id': 'Main', 'label': 'main.py'}, {'id': 'Tools', 'label': 'src/tools.py'}],
         'edges': [{'from': 'Main', 'to': 'Tools', 'label': '导入'}]}
DIAGRAMS = {'architecture': GRAPH, 'workflow': {**GRAPH, 'title': '处理流程'},
    'sequence': {'title': '模块交互', 'description': '入口调用工具并接收结果。',
                 'participants': [{'id': 'Main', 'label': '入口'}, {'id': 'Tools', 'label': '工具'}],
                 'messages': [{'from': 'Main', 'to': 'Tools', 'label': '处理任务'}]}}


@contextmanager
def stubborn_provider(force_reads=False):
    requests = []
    # This repeats the same core modules even when the previous result said
    # already_read. It never voluntarily chooses the old documentation action.
    order = ['README.md', 'main.py', 'src/agent.py', 'src/tools.py', 'src/rag.py',
             'README.md', 'requirements.txt', '.env.example', 'src/llm.py',
             'main.py', 'src/agent.py', 'src/context.py', 'src/memory.py',
             'src/tools.py', 'src/evaluate.py', 'src/rag.py', 'src/llm.py']
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append(request)
            name = request['tool_choice']['function']['name']
            assert name == 'submit_action'
            actions = request['tools'][0]['function']['parameters']['properties']['action']['enum']
            if 'read' in actions:
                index = len(requests) - 1
                arguments = {'action': 'inventory' if index == 0 else 'read',
                    'args': {'offset': 0} if index == 0 else {'path': order[(index - 1) % len(order)]},
                    'summary': '持续读取核心模块'}
                if force_reads and index >= 8:
                    arguments['args']['force'] = True
            elif actions == ['propose_documentation']:
                arguments = {'action': 'propose_documentation', 'summary': '提交项目说明', 'args': {
                    'overview': '# 阶段切换回归项目\n\n入口导入工具模块。仅静态解析，未运行项目。',
                    'diagrams': {**DIAGRAMS, **({'base_hashes': {'项目说明.md': 'forged'}} if force_reads else {})}}}
            else:
                arguments = {'action': 'final', 'args': {'message': '项目说明和设计图已自动应用。'}, 'summary': '完成'}
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Connection', 'close')
            self.end_headers()
            raw = json.dumps(arguments, ensure_ascii=False)
            for offset in range(0, len(raw), 120):
                part = {'index': 0, 'function': {'arguments': raw[offset:offset + 120]}}
                # Reproduce gateways that repeat full metadata on every chunk.
                part.update(id=f'real-phase-call-{len(requests)}', type='function')
                part['function']['name'] = name
                self.wfile.write(('data: ' + json.dumps({'choices': [{'delta': {'tool_calls': [part]},
                    'finish_reason': None}]}) + '\n\n').encode())
            self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}\n\ndata: [DONE]\n\n')
            self.wfile.flush()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/v1', requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def wait(client, task_id, status):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        task = client.get(f'/api/tasks/{task_id}').json()
        if task['status'] == status:
            return task
        if task['status'] in {'failed', 'interrupted', 'budget_exhausted'}:
            pytest.fail(str(task['result']))
        time.sleep(.02)
    pytest.fail(f"Expected {status}, got {task['status']}")


@pytest.mark.parametrize('force_reads', [False, True])
def test_stubborn_read_sequence_switches_native_tools_then_delivers_automatically(tmp_path, force_reads):
    root = tmp_path / 'project'
    root.mkdir()
    sources = {'README.md': '# 回归项目\n\n```powershell\npython main.py\n```\n',
        'requirements.txt': 'example-package==1.0\n', '.env.example': 'LLM_MODEL_ID=example\n',
        'main.py': 'from src.tools import handle\n\ndef main():\n    return handle()\n',
        'src/__init__.py': '# package\n', 'main.ipynb': '{"cells":[],"nbformat":4}\n'}
    for name in ['agent', 'tools', 'rag', 'llm', 'context', 'memory', 'evaluate']:
        sources[f'src/{name}.py'] = f'# 代码用途：实现 {name} 模块。\ndef handle():\n    return "{name}"\n'
    for path, content in sources.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode())
    with stubborn_provider(force_reads) as (base_url, requests):
        factory = lambda: HelloModel({'model': 'phase-test', 'base_url': base_url}, '')
        app = create_app(tmp_path / 'data', token='phase-test', model_factory=factory, persist_secrets=False)
        app.state.store.set_settings({'model': 'phase-test', 'base_url': base_url, 'max_steps': 40})
        with TestClient(app, headers={'Authorization': 'Bearer phase-test'}) as client:
            workspace = client.post('/api/workspaces', json={'path': str(root)}).json()
            created = client.post('/api/tasks', json={'workspace_id': workspace['id'],
                'prompt': '解析整个项目', 'skill': ANALYSIS_SKILL})
            assert created.status_code == 202
            task_id = created.json()['id']
            completed = wait(client, task_id, 'completed')
            names = [request['tools'][0]['function']['name'] for request in requests]
            assert set(names) == {'submit_action'}
            assert completed['steps'] <= len(sources) + 3
            pinned = json.loads(requests[-2]['messages'][1]['content'])['analysis_output']
            assert pinned['phase'] == 'draft' and pinned['read_files'] == len(sources)
            assert not pinned['next_files'] and not pinned['unavailable']
            schema = requests[-2]['tools'][0]['function']['parameters']['properties']
            assert schema['action']['enum'] == ['propose_documentation']
            assert set(schema['args']['properties']) == {'overview', 'diagrams'}
            assert 'baselines' not in pinned
            events = app.state.store.events(task_id)
            assert any(item['kind'] == 'analysis.read_planned' for item in events)
            assert not any(item['kind'] == 'agent.loop_warning' for item in events)
            assert completed['patches'][0]['status'] == 'applied'
            assert any(item['kind'] == 'patch.applied' and item['data'].get('automatic') for item in events)
            assert not any(item['kind'] == 'patch.proposed' for item in events)
            assert completed['steps'] == len(requests) and len(requests) <= len(sources) + 3
            assert requests[-1]['tools'][0]['function']['name'] == 'submit_action'
            assert requests[-1]['tools'][0]['function']['parameters']['properties']['action']['enum'] == ['final']
            assert json.loads(requests[-1]['messages'][1]['content'])['analysis_output']['phase'] == 'complete'
            actual_call = next(message for message in requests[-1]['messages'] if message.get('tool_calls')
                and json.loads(message['tool_calls'][0]['function']['arguments']).get('action') == 'propose_documentation')['tool_calls'][0]
            assert set(json.loads(actual_call['function']['arguments'])['args']) == {'overview', 'diagrams'}
            assert any(message.get('tool_call_id') == actual_call['id'] for message in requests[-1]['messages'])
            assert all((root / path).is_file() for path in OUTPUT_PATHS)
            assert all((root / path).read_bytes() == content.encode() for path, content in sources.items())


def test_repeated_reads_advance_unread_pages_without_claiming_unseen_lines(tmp_path):
    (tmp_path / 'main.py').write_bytes(b'value = 1\n')
    source = '# 项目说明\r\n' + ''.join(f'第 {index} 行说明代码的输入输出与模块关系。\r\n' for index in range(1600))
    (tmp_path / 'README.md').write_bytes(source.encode())
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    ctx.read({'path': 'main.py'})
    assert ctx.read({'path': 'main.py', 'force': True})['path'] == 'main.py'
    assert ctx.read({'path': 'main.py'})['path'] == 'main.py'
    parts, cursor = [], 1
    while ctx.phase() == 'inspect':
        value = ctx.read_planned()
        assert value['path'] == 'README.md'
        assert value['start_line'] == cursor
        cursor = value['end_line'] + 1
        parts.append(value['content'])
    assert ''.join(parts) == source and len(parts) > 2
    assert ctx.phase() == 'draft' and not ctx.snapshot()['next_files']


def test_unreadable_file_is_reported_once_and_shared_page_limit_is_not_a_file_failure(tmp_path):
    (tmp_path / 'main.py').write_bytes(b'value = 1\n')
    large = tmp_path / 'other.py'
    large.write_bytes(b'value = "' + b'x' * 6000 + b'"\n')
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    ctx.read({'path': 'main.py'})
    short = ctx.read({'path': 'main.py'}, max_chars=1000)
    assert short['status'] == 'already_read' and short['path'] == 'main.py'
    with pytest.raises(ReadCapacityError):
        ctx.read({'path': 'other.py'}, max_chars=1000)
    assert not ctx.blocked and 'other.py' not in ctx.reads
    assert ctx.read_planned()['path'] == 'other.py'
    large.write_bytes(b'x' * 256001)
    fresh = AnalysisContext(Workspace(str(tmp_path)))
    actual = fresh.read({'path': 'main.py'})
    blocked = fresh.read_planned()
    assert blocked['status'] == 'blocked' and fresh.phase() == 'draft'
    assert fresh.snapshot()['unavailable'][0]['path'] == 'other.py'
    history = [{'role': 'user', 'content': '工具观察：' + json.dumps(value)} for value in [actual, blocked]]
    assert AnalysisContext(Workspace(str(tmp_path)), history).phase() == 'draft'


@pytest.mark.parametrize('style', ['direct', 'old_envelope', 'missing_outer', 'summary'])
def test_documentation_tool_normalizes_only_complete_envelopes_without_changing_text(style):
    args = {'overview': '# 中文\n包含 "引号" 与 ``` 围栏。', 'diagrams': DIAGRAMS}
    payload = {'action': 'propose_documentation', 'args': args} if style == 'old_envelope' else dict(args)
    if style == 'summary': payload['summary'] = '准备说明'
    raw = json.dumps(payload, ensure_ascii=False)
    if style == 'missing_outer': raw = raw[:-1]
    assert documentation_action('propose_documentation', raw)['args'] == args


def test_phase_tools_offer_only_document_submission_then_completion():
    draft = action_tool(analysis_mode=True, analysis_phase='draft')['function']
    complete = action_tool(analysis_mode=True, analysis_phase='complete')['function']
    assert draft['name'] == complete['name'] == 'submit_action'
    assert draft['parameters']['properties']['action']['enum'] == ['propose_documentation']
    assert 'path' not in draft['parameters']['properties']['args']['properties']
    assert complete['parameters']['properties']['action']['enum'] == ['final']
    assert complete['parameters']['properties']['args']['required'] == ['message']
    with pytest.raises(ActionFormatError):
        documentation_action('propose_documentation', '{"action":"read","args":{"path":"main.py"}}')


@pytest.mark.parametrize('location', ['args', 'diagrams', 'envelope', 'both'])
def test_obsolete_version_fields_are_discarded_without_modifying_document_content(location):
    expected = {'overview': '# 文档\n包含 base_hashes 字样。', 'diagrams': copy.deepcopy(DIAGRAMS)}
    args = copy.deepcopy(expected)
    if location in {'args', 'both'}:
        args['base_hashes'] = {'项目说明.md': 'forged'}
    if location in {'diagrams', 'both'}:
        args['diagrams']['base_hashes'] = ['not-even-a-hash-map']
    payload = {'action': 'propose_documentation', 'args': args, 'summary': '提交文档'}
    if location == 'envelope':
        payload['base_hashes'] = None
    original = copy.deepcopy(payload)
    result = documentation_action('propose_documentation', json.dumps(payload, ensure_ascii=False))
    assert result['args'] == expected and payload == original


@pytest.mark.parametrize('args,path', [
    ({'overview': '说明'}, 'args.diagrams'),
    ({'diagrams': DIAGRAMS}, 'args.overview'),
    ({'overview': [], 'diagrams': DIAGRAMS}, 'args.overview'),
    ({'overview': '说明', 'diagrams': []}, 'args.diagrams'),
    ({'overview': '说明', 'diagrams': {key: value for key, value in DIAGRAMS.items() if key != 'sequence'}}, 'args.diagrams.sequence'),
    ({'overview': '说明', 'diagrams': {**DIAGRAMS, 'wrong': {}}}, 'args.diagrams.wrong'),
    ({'overview': '说明', 'diagrams': DIAGRAMS, 'path': 'main.py'}, 'args.path'),
])
def test_documentation_errors_identify_exact_field(args, path):
    with pytest.raises(ActionFormatError) as error:
        documentation_action('propose_documentation', json.dumps(args))
    assert path in str(error.value)


def test_old_saved_instructions_are_adapted_without_exposing_or_changing_client_baselines():
    from backend.runtime import context_messages
    task = {'prompt': '解析项目', 'selected_file': None, 'test_argv': '[]', 'skill': ANALYSIS_SKILL,
            'skill_instructions': '通过 propose_documentation 一次提交 overview、diagrams 与 analysis_output.baselines 对应的完整 base_hashes。',
            'analysis_output': {'phase': 'draft', 'baselines': dict.fromkeys(OUTPUT_PATHS, 'missing')}}
    before = copy.deepcopy(task)
    messages = context_messages([], task)
    assert 'args 仅包含 overview、diagrams' in messages[0]['content']
    assert 'base_hashes' not in messages[0]['content']
    assert 'baselines' not in json.loads(messages[1]['content'])['analysis_output']
    assert task == before
