"""Project analysis delivers fixed Markdown and locally rendered, reviewable PNGs."""
import base64
import copy
import io
import json
import random
import time
from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.analysis_context import AnalysisContext
from backend.analysis_documents import ANALYSIS_SKILL, OUTPUT_PATHS, analysis_baselines, build_analysis_bundle
from backend.app import create_app
from backend.model import ModelProtocolError, action_tool, native_read_batch, tool_messages
from backend.skills import load_skill
from backend.workspace import Conflict, Workspace


SOURCE = 'def add(left, right):\n    return left + right\n'
OVERVIEW = '# 计算器项目说明\n\n## 项目概述\n提供整数加法。\n\n## 验证方式\n可运行 pytest；本次未执行。\n'
AUTH = {'Authorization': 'Bearer documentation-test'}
GRAPH = {'title': '计算器系统架构', 'description': '调用方通过真实 add 函数得到相加结果。',
         'nodes': [{'id': 'Caller', 'label': '调用方'}, {'id': 'Add', 'label': 'main.py 加法函数'}],
         'edges': [{'from': 'Caller', 'to': 'Add', 'label': '调用'}]}
DIAGRAMS = {'architecture': GRAPH, 'workflow': {**GRAPH, 'title': '加法执行流程'},
    'sequence': {'title': '加法调用时序', 'description': '调用方传入两个参数，由函数返回和。',
        'participants': [{'id': 'Caller', 'label': '调用方'}, {'id': 'Add', 'label': '加法函数'}],
        'messages': [{'from': 'Caller', 'to': 'Add', 'label': '传入 left 和 right'},
                     {'from': 'Add', 'to': 'Caller', 'label': '返回相加结果', 'dashed': True}]}}


def action(name, **args):
    return json.dumps({'action': name, 'args': args, 'summary': name}, ensure_ascii=False)


def package_action(messages):
    return action('propose_documentation', overview=OVERVIEW, diagrams=DIAGRAMS)


def wait(s, task_id, status):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        task = s.client.get(f'/api/tasks/{task_id}').json()
        if task['status'] == status:
            return task
        if task['status'] == 'failed':
            pytest.fail(task['result'])
        time.sleep(.01)
    pytest.fail(f"Expected {status}, got {task['status']}")


@pytest.fixture
def service(tmp_path, monkeypatch):
    class Registry:
        def register_function(self, *args):
            pass
    monkeypatch.setattr('backend.runtime.create_tool_registry', Registry)
    queue, seen = deque(), []
    class Model:
        async def generate(self, messages, emit):
            seen.append(messages)
            response = queue.popleft()
            self.last_tool_calls = []
            if isinstance(response, tuple):
                response, self.last_tool_calls = response
            return response(messages) if callable(response) else response
        def close(self):
            pass
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'main.py').write_bytes(SOURCE.encode())
    (root / 'README.md').write_text('# 保留原说明\n', encoding='utf-8')
    app = create_app(tmp_path / 'service', token='documentation-test', model_factory=Model, persist_secrets=False)
    app.state.store.set_settings({'model': 'local-test', 'base_url': 'https://example.invalid/v1', 'max_steps': 50})
    with TestClient(app, headers=AUTH) as client:
        workspace = client.post('/api/workspaces', json={'path': str(root)}).json()
        def create(**extra):
            response = client.post('/api/tasks', json={'workspace_id': workspace['id'],
                'skill': ANALYSIS_SKILL, 'prompt': '说明本项目并生成 docs 三图。', **extra})
            assert response.status_code == 202, response.text
            return response.json()['id']
        yield SimpleNamespace(app=app, client=client, root=root, queue=queue, seen=seen, create=create, workspace=workspace)


def test_bundle_is_bounded_real_png_and_links_all_five_outputs_without_writes(tmp_path):
    workspace = Workspace(str(tmp_path))
    bundle = build_analysis_bundle(workspace, OVERVIEW, DIAGRAMS, analysis_baselines(workspace))
    assert {item['path'] for item in bundle} == set(OUTPUT_PATHS)
    assert not list(tmp_path.iterdir())
    for item in bundle:
        if item['path'].endswith('.png'):
            raw = base64.b64decode(item['content'], validate=True)
            assert raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw) <= 256000
            with Image.open(io.BytesIO(raw)) as image:
                assert image.format == 'PNG' and image.width > 500 and image.height > 300
                image.verify()
        elif item['path'] == '项目说明.md':
            assert all(f'docs/diagrams/{name}.png' in item['content'] for name in ('architecture', 'workflow', 'sequence'))
        else:
            assert '../../项目说明.md' in item['content'] and '计算器系统架构' in item['content']


@pytest.mark.parametrize('bad', ['unknown_edge', 'duplicate_id', 'unknown_actor', 'oversized', 'extra_path', 'notext'])
def test_invalid_specs_or_baselines_cannot_write_artifacts(tmp_path, bad):
    diagrams = copy.deepcopy(DIAGRAMS)
    workspace = Workspace(str(tmp_path))
    hashes, overview = analysis_baselines(workspace), OVERVIEW
    if bad == 'unknown_edge': diagrams['architecture']['edges'][0]['to'] = 'Missing'
    elif bad == 'duplicate_id': diagrams['architecture']['nodes'][1]['id'] = 'Caller'
    elif bad == 'unknown_actor': diagrams['sequence']['messages'][0]['from'] = 'Missing'
    elif bad == 'oversized': diagrams['workflow']['nodes'] *= 20
    elif bad == 'extra_path': hashes['../README.md'] = 'missing'
    else: overview = ''
    with pytest.raises(ValueError): build_analysis_bundle(workspace, overview, diagrams, hashes)
    assert not list(tmp_path.iterdir())


def test_analysis_accepts_existing_large_png_baseline_and_detects_changed_artifact(tmp_path):
    path = tmp_path / OUTPUT_PATHS[2]
    path.parent.mkdir(parents=True)
    image = Image.frombytes('RGB', (400, 400), random.Random(7).randbytes(400 * 400 * 3))
    image.save(path, 'PNG')
    assert path.stat().st_size > 256000
    workspace = Workspace(str(tmp_path))
    hashes = analysis_baselines(workspace)
    (tmp_path / '项目说明.md').write_text('用户后来补充的说明', encoding='utf-8')
    with pytest.raises(Conflict): build_analysis_bundle(workspace, OVERVIEW, DIAGRAMS, hashes)
    assert (tmp_path / '项目说明.md').read_text(encoding='utf-8') == '用户后来补充的说明'


def test_project_analysis_reads_source_auto_applies_all_outputs_and_undoes(service):
    s = service
    s.queue.extend([action('read', path='main.py'), package_action, action('final', message='文档交付完成。')])
    task_id = s.create(selected_file='main.py')
    completed = wait(s, task_id, 'completed')
    assert completed['selected_file'] is None and completed['skill'] == ANALYSIS_SKILL
    assert completed['test_argv'] == [] and len(completed['patches']) == 1
    assert completed['patches'][0]['status'] == 'applied'
    assert len(completed['patches'][0]['changes']) == 5
    assert 'baselines' not in json.loads(s.seen[0][1]['content'])['analysis_output']
    assert load_skill(ANALYSIS_SKILL) in s.seen[0][0]['content']
    events = s.app.state.store.events(task_id)
    assert not any(event['kind'] == 'patch.proposed' for event in events)
    assert any(event['kind'] == 'patch.applied' and event['data'].get('automatic') for event in events)
    observation = json.loads(s.seen[-1][-1]['content'][5:])
    assert observation['status'] == 'applied' and observation['files'] == list(OUTPUT_PATHS)
    assert completed['steps'] == 3 and all((s.root / path).is_file() for path in OUTPUT_PATHS)
    assert '未执行目标项目或测试' in completed['result']
    assert (s.root / 'main.py').read_bytes() == SOURCE.encode()
    assert (s.root / 'README.md').read_text(encoding='utf-8') == '# 保留原说明\n'
    response = s.client.post(f"/api/patches/{completed['patches'][0]['id']}/undo")
    assert response.status_code == 200, response.text
    assert all(not (s.root / path).exists() for path in OUTPUT_PATHS)


def test_invalid_documentation_never_auto_applies_outputs(service):
    s = service
    diagrams = copy.deepcopy(DIAGRAMS)
    diagrams['architecture']['edges'][0]['to'] = 'Missing'
    invalid = action('propose_documentation', overview=OVERVIEW, diagrams=diagrams)
    def corrected_package(messages):
        assert all(not (s.root / path).exists() for path in OUTPUT_PATHS)
        return package_action(messages)
    s.queue.extend([action('read', path='main.py'), invalid, invalid, invalid,
                    action('read', path='README.md'), corrected_package, action('final', message='已完成')])
    task_id = s.create()
    completed = wait(s, task_id, 'completed')
    assert len(completed['patches']) == 1 and completed['patches'][0]['status'] == 'applied'
    errors = [event for event in s.app.state.store.events(task_id) if event['kind'] == 'tool.error']
    assert len(errors) == 3
    assert all('Missing' in event['data']['message'] or '节点' in event['data']['message'] for event in errors)


@pytest.mark.parametrize('legacy_location', [None, 'args', 'diagrams'])
def test_external_document_change_stops_auto_apply_without_trusting_model_hashes(service, legacy_location):
    s = service
    def changed_while_model_was_generating(messages):
        (s.root / '项目说明.md').write_text('用户补充的原说明', encoding='utf-8')
        payload = json.loads(package_action(messages))
        if legacy_location:
            container = payload['args'] if legacy_location == 'args' else payload['args']['diagrams']
            # A provider can supply the newest real versions; they must never
            # replace the client's trusted snapshot taken before this request.
            container['base_hashes'] = analysis_baselines(Workspace(str(s.root)))
        return json.dumps(payload, ensure_ascii=False)
    s.queue.extend([action('read', path='main.py'), changed_while_model_was_generating])
    stopped = wait(s, s.create(), 'interrupted')
    assert stopped['steps'] == 2 and not stopped['patches']
    assert (s.root / '项目说明.md').read_text(encoding='utf-8') == '用户补充的原说明'
    assert all('baselines' not in json.loads(prompt[1]['content'])['analysis_output'] for prompt in s.seen)
    assert any(event['kind'] == 'tool.error' and '交付文件已变化' in event['data']['message']
               for event in s.app.state.store.events(stopped['id']))
    assert all(not (s.root / path).exists() for path in OUTPUT_PATHS[1:])
    assert '自动应用已停止' in stopped['result'] and len(s.seen) == 2


def test_document_edit_between_proposal_and_auto_apply_conflicts_without_overwriting(service, monkeypatch):
    s = service
    apply = s.app.state.runtime.patches.apply
    def concurrent_edit(patch_id):
        (s.root / '项目说明.md').write_text('写入前用户修改', encoding='utf-8')
        return apply(patch_id)
    monkeypatch.setattr(s.app.state.runtime.patches, 'apply', concurrent_edit)
    s.queue.extend([action('read', path='main.py'), package_action])
    stopped = wait(s, s.create(), 'interrupted')
    assert stopped['steps'] == 2 and len(stopped['patches']) == 1
    assert stopped['patches'][0]['status'] == 'conflicted'
    assert (s.root / '项目说明.md').read_text(encoding='utf-8') == '写入前用户修改'
    assert all(not (s.root / path).exists() for path in OUTPUT_PATHS[1:])


def test_auto_apply_write_failure_rolls_back_and_stops_without_regenerating(service, monkeypatch):
    s = service
    write = s.app.state.runtime.patches.write
    def disk_failure(path, content, mode=None):
        if path.name == 'README.md' and path.parent.name == 'diagrams':
            raise OSError('simulated disk failure')
        return write(path, content, mode)
    monkeypatch.setattr(s.app.state.runtime.patches, 'write', disk_failure)
    s.queue.extend([action('read', path='main.py'), package_action])
    stopped = wait(s, s.create(), 'failed')
    assert stopped['steps'] == 2 and len(stopped['patches']) == 1
    assert stopped['patches'][0]['status'] == 'rejected'
    assert '自动应用失败' in stopped['result']
    assert all(not (s.root / path).exists() for path in OUTPUT_PATHS)
    assert (s.root / 'main.py').read_bytes() == SOURCE.encode()


def test_auto_applied_document_package_restores_existing_markdown_and_pngs_on_undo(service):
    s = service
    workspace = Workspace(str(s.root))
    before = {}
    old_bundle = build_analysis_bundle(workspace, '# 用户之前的说明', DIAGRAMS, analysis_baselines(workspace))
    for change in old_bundle:
        target = s.root / change['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(change['content']) if change.get('encoding') == 'base64' else change['content'].encode()
        target.write_bytes(raw)
        before[change['path']] = raw
    s.queue.extend([action('read', path='main.py'), package_action, action('final', message='重新生成完成')])
    completed = wait(s, s.create(), 'completed')
    patch = completed['patches'][0]
    assert patch['status'] == 'applied' and len(patch['changes']) == 5
    assert (s.root / '项目说明.md').read_bytes() != before['项目说明.md']
    assert s.client.post(f"/api/patches/{patch['id']}/undo").status_code == 200
    assert all((s.root / path).read_bytes() == raw for path, raw in before.items())


def test_edit_after_auto_apply_does_not_refresh_baselines_or_overwrite_again(service, monkeypatch):
    s = service
    emit = s.app.state.runtime.emit
    async def edit_after_apply(task_id, kind, data):
        await emit(task_id, kind, data)
        if kind == 'patch.applied':
            (s.root / '项目说明.md').write_text('自动应用之后的用户修改', encoding='utf-8')
    monkeypatch.setattr(s.app.state.runtime, 'emit', edit_after_apply)
    s.queue.extend([action('read', path='main.py'), package_action])
    stopped = wait(s, s.create(), 'failed')
    assert len(s.seen) == 2 and len(stopped['patches']) == 1
    assert stopped['patches'][0]['status'] == 'applied'
    assert (s.root / '项目说明.md').read_text(encoding='utf-8') == '自动应用之后的用户修改'
    assert '已发生变化' in stopped['result']


@pytest.mark.parametrize('initial', ['final', 'package'])
def test_final_and_bundle_require_real_source_evidence_and_delivered_files(service, initial):
    s = service
    s.queue.extend([action('final', message='不能提前宣称完成。') if initial == 'final' else package_action,
        action('read', path='main.py'), package_action, action('final', message='已确认交付。')])
    task_id = s.create()
    completed = wait(s, task_id, 'completed')
    assert any(event['kind'] == 'tool.error' for event in s.app.state.store.events(task_id))
    assert completed['steps'] == 4


def test_static_documentation_rejects_execution_and_generic_source_patches(service):
    s = service
    invalid = s.client.post('/api/tasks', json={'workspace_id': s.workspace['id'], 'skill': ANALYSIS_SKILL,
        'prompt': '说明项目', 'test_argv': ['python', '-m', 'pytest']})
    assert invalid.status_code == 400
    s.queue.extend([action('propose_patch', changes=[{'path': 'main.py', 'base_hash': 'missing', 'content': 'bad'}])] * 6)
    task_id = s.create()
    assert wait(s, task_id, 'interrupted')['steps'] == 6
    stopped = [event for event in s.app.state.store.events(task_id)
               if '持续重复动作或无进展，已停止' in event['data'].get('message', '')]
    assert len(stopped) == 1
    assert (s.root / 'main.py').read_bytes() == SOURCE.encode()
    assert not s.client.get(f'/api/tasks/{task_id}').json()['patches']


def test_analysis_read_pages_preserve_full_hash_and_fixed_evidence_after_context_loss(tmp_path):
    source = ''.join(f'value_{i} = {i}\r\n' for i in range(3000))
    (tmp_path / 'large.py').write_bytes(source.encode())
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    parts, hashes, start = [], set(), 1
    while start is not None:
        value = ctx.read({'path': 'large.py', 'start_line': start})
        parts.append(value['content'])
        hashes.add(value['hash'])
        start = value['next_start_line']
    assert ''.join(parts) == source and len(parts) > 3 and len(hashes) == 1
    snapshot = ctx.snapshot()
    assert snapshot['read_files'] == 1 and snapshot['evidence'][0]['ranges'] == [[1, 3000]]
    assert len(json.dumps(snapshot, ensure_ascii=False)) <= 8000


def test_analysis_native_schema_exposes_only_documentation_submission_and_safe_reads():
    schema = action_tool(analysis_mode=True)['function']['parameters']['properties']
    assert 'propose_documentation' in schema['action']['enum']
    assert not {'propose_patch', 'test', 'annotate_unit'}.intersection(schema['action']['enum'])
    args = schema['args']['properties']
    assert 'base_hashes' not in args
    assert set(args['diagrams']['required']) == {'architecture', 'workflow', 'sequence'}


def test_completed_reads_return_compact_evidence_but_force_and_external_edits_still_read_source(tmp_path):
    source = '# 代码用途：提供相加入口。\nfrom math import floor\n' + SOURCE
    path = tmp_path / 'main.py'
    path.write_bytes(source.encode('utf-8'))
    (tmp_path / 'requirements.txt').write_text('example-package==1.0\n', encoding='utf-8')
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    first = ctx.read({'path': 'main.py'})
    token = ctx.token()
    repeated = ctx.read({'path': 'main.py'})
    assert first['content'] == source and repeated['status'] == 'already_read'
    assert 'content' not in repeated and repeated['fully_read']
    assert repeated['next_files'] == [{'path': 'requirements.txt', 'start_line': 1}]
    assert ctx.token() == token
    snapshot = ctx.snapshot()
    assert snapshot['evidence'][0]['excerpt'] == '# 代码用途：提供相加入口。'
    assert snapshot['evidence'][0]['definitions'] == ['add']
    assert snapshot['evidence'][0]['imports'] == ['math']
    assert ctx.read({'path': 'main.py', 'force': True})['content'] == source
    changed = source + 'extra = True\n'
    path.write_bytes(changed.encode('utf-8'))
    actual = ctx.read({'path': 'main.py'})
    assert actual['content'] == changed and actual['hash'] != first['hash']
    assert ctx.token() != token


def test_implicit_long_reads_continue_unread_pages_and_restore_real_coverage(tmp_path):
    source = ''.join(f'value_{i} = {i}\r\n' for i in range(3000))
    (tmp_path / 'large.py').write_bytes(source.encode())
    workspace = Workspace(str(tmp_path))
    ctx = AnalysisContext(workspace)
    first = ctx.read({'path': 'large.py'})
    duplicate = ctx.read({'path': 'large.py', 'start_line': 1, 'end_line': first['end_line']})
    assert duplicate['status'] == 'already_read' and not duplicate['fully_read']
    messages = [{'role': 'user', 'content': '工具观察：' + json.dumps(first)}]
    restored = AnalysisContext(workspace, messages)
    second = restored.read({'path': 'large.py'})
    assert second['start_line'] == first['next_start_line']
    parts = [first['content'], second['content']]
    while restored.snapshot()['next_action'] == 'read':
        parts.append(restored.read({'path': 'large.py'})['content'])
    assert ''.join(parts) == source
    assert restored.read({'path': 'large.py'})['status'] == 'already_read'
    assert restored.read({'path': 'large.py', 'start_line': 2, 'end_line': 2, 'force': True})['content'] == source.splitlines(keepends=True)[1]


def test_project_analysis_root_listing_and_repeat_read_can_advance_to_document_review(service):
    s = service
    (s.root / 'requirements.txt').write_text('example-package==1.0\n', encoding='utf-8')
    (s.root / 'other.py').write_text('# 代码用途：提供辅助值。\nvalue = 1\n', encoding='utf-8')
    def follow_remaining_evidence(messages):
        pinned = json.loads(messages[1]['content'])['analysis_output']
        next_files = pinned['next_files']
        return action('read', **next_files[0]) if next_files else package_action(messages)
    s.queue.extend([action('list', path='.'), action('read', path='main.py'),
        action('read', path='main.py'), *([follow_remaining_evidence] * 4), action('final', message='自动交付完成')])
    pending = wait(s, s.create(), 'completed')
    assert pending['steps'] == 8
    events = s.app.state.store.events(pending['id'])
    assert any(event['kind'] == 'analysis.read_cached' for event in events)
    assert not any(event['kind'] in {'tool.error', 'agent.loop_warning'} for event in events)
    snapshot = json.loads(s.seen[-2][1]['content'])['analysis_output']
    assert snapshot['next_action'] == 'propose_documentation' and not snapshot['next_files']
    assert all(entry['fully_read'] for entry in snapshot['evidence'])
    assert len(pending['patches'][0]['changes']) == 5


def test_native_batch_reads_are_bounded_restored_after_review_and_keep_individual_errors(service):
    s = service
    source = ''.join(f'value_{i} = {i}\r\n' for i in range(3000))
    (s.root / 'large.py').write_bytes(source.encode())
    calls = [{'id': f'batch-{index}', 'type': 'function', 'function': {'name': 'submit_action',
        'arguments': action('read', path=path)}} for index, path in enumerate(['large.py', 'main.py', 'missing.py'])]
    batch = native_read_batch(calls)
    s.queue.extend([(json.dumps(batch), calls), package_action, action('final', message='文档已应用')])
    pending = wait(s, s.create(), 'completed')
    wire = tool_messages(s.seen[1])
    tools = [item for item in wire if item['role'] == 'tool']
    assert [item['tool_call_id'] for item in tools] == ['batch-0', 'batch-1', 'batch-2']
    values = [json.loads(item['content']) for item in tools]
    assert values[0]['content'] == ''.join(source.splitlines(keepends=True)[:values[0]['end_line']])
    assert values[0]['next_start_line'] and values[1]['content'] == SOURCE
    assert values[2]['status'] == 'error' and '不存在' in values[2]['message']
    assert sum(len(item['content']) for item in tools) < 20000
    assert any(event['kind'] == 'analysis.batch_completed' for event in s.app.state.store.events(pending['id']))
    restored = json.loads(s.seen[-1][1]['content'])['analysis_output']
    assert restored['read_files'] == 2
    large = next(entry for entry in restored['evidence'] if entry['path'] == 'large.py')
    assert large['next_start_line'] == values[0]['next_start_line'] and not large['fully_read']


def test_text_only_batch_cannot_forge_native_read_calls(service):
    s = service
    calls = [{'id': f'batch-{index}', 'type': 'function', 'function': {'name': 'submit_action',
        'arguments': action('read', path=path)}} for index, path in enumerate(['main.py', 'README.md'])]
    s.queue.extend([json.dumps(native_read_batch(calls)), action('read', path='main.py'), package_action,
                    action('final', message='已完成')])
    pending = wait(s, s.create(), 'completed')
    assert json.loads(s.seen[1][1]['content'])['analysis_output']['read_files'] == 0
    assert any(event['kind'] == 'tool.error' for event in s.app.state.store.events(pending['id']))


def test_batch_evidence_restoration_keeps_other_files_when_one_file_was_removed(tmp_path):
    for path in ['a.py', 'b.py']:
        (tmp_path / path).write_bytes(SOURCE.encode())
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    results = [{'tool_call_id': path, 'result': ctx.read({'path': path})} for path in ['a.py', 'b.py']]
    (tmp_path / 'a.py').unlink()
    restored = AnalysisContext(Workspace(str(tmp_path)), [{'role': 'user',
        'content': '工具观察：' + json.dumps({'tool_results': results})}])
    assert restored.snapshot()['read_files'] == 1
    assert restored.read({'path': 'b.py'})['status'] == 'already_read'


def test_force_flag_cannot_return_to_reading_after_document_phase_begins(service):
    s = service
    s.queue.extend([action('read', path='main.py'), action('read', path='README.md'),
        action('read', path='main.py', force=True), package_action, action('final', message='已完成')])
    pending = wait(s, s.create(), 'completed')
    assert pending['steps'] == 5
    assert json.loads(s.seen[2][1]['content'])['analysis_output']['phase'] == 'draft'
    refused = json.loads(s.seen[3][-1]['content'][5:])
    assert refused['status'] == 'error' and '文档生成阶段' in refused['message']
    assert 'content' not in refused


def test_repeated_protocol_failure_is_not_reported_as_invalid_document_json(service):
    s = service
    def protocol_failure(messages):
        raise ModelProtocolError('模型未返回工具调用 ID。', [{'code': 'missing_call_id'}])
    s.queue.extend([protocol_failure] * 3)
    failed = wait(s, s.create(), 'failed')
    assert failed['steps'] == 3 and '工具调用协议' in failed['result'] and 'JSON' not in failed['result']
    errors = [event for event in s.app.state.store.events(failed['id']) if event['kind'] == 'tool.error']
    assert len(errors) == 3 and all('工具协议错误' in event['data']['message'] for event in errors)
