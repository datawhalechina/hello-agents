"""Final JSON sizing, rollback and deferred reads at shared-page boundaries."""
import json

import pytest

from backend.analysis_context import AnalysisContext, ReadCapacityError
from backend.model import native_read_batch
from backend.runtime import Runtime
from backend.workspace import Workspace


class MemoryStore:
    def __init__(self):
        self.events = []
        self.saved = {}

    def event(self, task_id, kind, data):
        self.events.append({'kind': kind, 'data': data})

    def update_task(self, task_id, **values):
        self.saved.update(values)


def service(tmp_path):
    store = MemoryStore()
    return AnalysisContext(Workspace(str(tmp_path))), Runtime(store, None), store


def calls_for(paths):
    return [{'id': f'actual-call-{index}-' + 'x' * 160, 'type': 'function', 'function': {
        'name': 'submit_action', 'arguments': json.dumps({'action': 'read', 'args': {'path': path},
                                                       'summary': '读取真实文件'})}}
            for index, path in enumerate(paths)]


@pytest.mark.asyncio
async def test_four_near_limit_results_fit_including_call_ids_and_json_envelopes(tmp_path):
    originals = {}
    for path in ['a.py', 'b.py', 'c.py', 'd.py']:
        source = ''.join(f'value_{index} = {repr("中文" * 20 + chr(92) * 4)}\r\n' for index in range(300))
        (tmp_path / path).write_bytes(source.encode())
        originals[path] = source
    ctx, runtime, store = service(tmp_path)
    calls = calls_for(originals)
    observation = await runtime.analysis_read_batch('test', ctx, {}, native_read_batch(calls)['args'], calls)
    assert 17000 < len(observation) <= 18000
    results = json.loads(observation)['tool_results']
    for call, result in zip(calls, results):
        value = result['result']
        path = json.loads(call['function']['arguments'])['args']['path']
        assert value['path'] == path and 'status' not in value
        assert value['content'] == ''.join(originals[path].splitlines(keepends=True)[:value['end_line']])
        assert ctx.reads[path]['ranges'] == [[1, value['end_line']]]
        assert not ctx.reads[path]['fully_read']
    assert store.events[-1]['data']['succeeded'] == 4
    assert store.events[-1]['data']['failed'] == store.events[-1]['data']['deferred'] == 0
    # An already-read request must never turn into a different file.
    before = ctx.token()
    cached = ctx.read({'path': 'a.py', 'start_line': 1, 'end_line': 1}, max_chars=500)
    assert cached['status'] == 'already_read' and cached['path'] == 'a.py'
    assert len(json.dumps(cached, ensure_ascii=False)) <= 500 and ctx.token() == before


@pytest.mark.asyncio
async def test_long_lines_are_automatically_deferred_and_read_without_another_model_call(tmp_path):
    originals = {'a.py': 'value = "' + 'a' * 7000 + '"\r\n',
                 'b.py': 'value = "' + 'b' * 7000 + '"\r\n',
                 'c.py': 'value = 3\r\n', 'd.py': 'value = 4\r\n'}
    for path, source in originals.items():
        (tmp_path / path).write_bytes(source.encode())
    ctx, runtime, store = service(tmp_path)
    calls = calls_for(originals)
    observation = await runtime.analysis_read_batch('test', ctx, {}, native_read_batch(calls)['args'], calls)
    values = [item['result'] for item in json.loads(observation)['tool_results']]
    deferred = [item for item in values if item.get('status') == 'deferred']
    assert deferred and ctx.deferred_reads
    assert all(item['path'] not in ctx.reads for item in deferred)
    assert all(item.get('status') != 'error' for item in values)
    messages = [{'role': 'user', 'content': '工具观察：' + observation}]
    await runtime.complete_deferred_reads('test', ctx, messages)
    assert not ctx.deferred_reads and ctx.phase() == 'draft'
    for item in deferred:
        path = item['path']
        delivered = [json.loads(message['content'][5:]) for message in messages[1:]]
        assert ''.join(value['content'] for value in delivered if value.get('path') == path) == originals[path]
    restored = AnalysisContext(Workspace(str(tmp_path)), messages)
    assert restored.phase() == 'draft' and not restored.deferred_reads


@pytest.mark.asyncio
async def test_rejected_final_result_rolls_back_coverage_before_retry(tmp_path, monkeypatch):
    (tmp_path / 'a.py').write_bytes(b'value = 1\n')
    (tmp_path / 'b.py').write_bytes(b'value = 2\n')
    ctx, runtime, store = service(tmp_path)
    original_read = ctx.read
    attempted = False
    def postprocessed_read(args, *, max_chars=18000):
        nonlocal attempted
        value = original_read(args, max_chars=max_chars)
        if args['path'] == 'a.py' and not attempted:
            attempted = True
            value['late_transport_metadata'] = 'x' * max_chars
        return value
    monkeypatch.setattr(ctx, 'read', postprocessed_read)
    calls = calls_for(['a.py', 'b.py'])
    observation = await runtime.analysis_read_batch('test', ctx, {}, native_read_batch(calls)['args'], calls)
    assert json.loads(observation)['tool_results'][0]['result']['status'] == 'deferred'
    assert 'a.py' not in ctx.reads and ctx.reads['b.py']['fully_read']
    assert ctx.phase() == 'inspect'
    await runtime.complete_deferred_reads('test', ctx, [])
    assert ctx.reads['a.py']['fully_read'] and ctx.phase() == 'draft'


def test_page_too_small_does_not_credit_source_or_mark_a_file_blocked(tmp_path):
    (tmp_path / 'a.py').write_bytes(b'value = "' + b'x' * 6000 + b'"\n')
    ctx = AnalysisContext(Workspace(str(tmp_path)))
    before = ctx.token()
    with pytest.raises(ReadCapacityError):
        ctx.read({'path': 'a.py'}, max_chars=4500)
    assert ctx.token() == before and not ctx.reads and not ctx.blocked
