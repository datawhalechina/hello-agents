"""Native read batches retain every real call ID and reject mixed side effects."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from backend.analysis_documents import ANALYSIS_SKILL
from backend.model import ActionFormatError, HelloModel, ModelOutputTruncated, ModelProtocolError, native_read_batch, parse_action, tool_messages


def native(index, action='read', **args):
    return {'id': f'actual-read-{index}', 'type': 'function', 'function': {
        'name': 'submit_action', 'arguments': json.dumps({'action': action, 'args': args,
            'summary': f'读取真实文件 {index}'}, ensure_ascii=False)}}


@contextmanager
def streaming_model(calls, finish='tool_calls', metadata='first'):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Connection', 'close')
            self.end_headers()
            current = calls if len(requests) == 1 else [native(99, 'final', message='真实结果已收到')]
            for half in (0, 1):
                parts = []
                for index, call in enumerate(current):
                    arguments = call['function']['arguments']
                    middle = len(arguments) // 2
                    part = {'index': index, 'function': {'arguments': arguments[:middle] if half == 0 else arguments[middle:]}}
                    if half == 0 or metadata != 'first':
                        part.update(id=call['id'], type='function')
                        part['function']['name'] = call['function']['name']
                        if metadata in {'cumulative', 'fragment'}:
                            name = call['function']['name']
                            identifier = call['id']
                            part['function']['name'] = name[:7] if half == 0 else name if metadata == 'cumulative' else name[7:]
                            part['id'] = identifier[:6] if half == 0 else identifier if metadata == 'cumulative' else identifier[6:]
                    parts.append(part)
                chunk = {'choices': [{'index': 0, 'delta': {'content': 'fabricated tool observation',
                    'tool_calls': parts}, 'finish_reason': None}]}
                self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
            ending = {'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]}
            self.wfile.write(('data: ' + json.dumps(ending) + '\n\ndata: [DONE]\n\n').encode())
            self.wfile.flush()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    model = HelloModel({'model': 'batch-protocol-test', 'base_url': f'http://127.0.0.1:{server.server_port}/v1'}, '')
    try:
        yield SimpleNamespace(model=model, requests=requests)
    finally:
        model.close()
        server.shutdown()
        server.server_close()
        thread.join()


MESSAGES = [{'role': 'system', 'content': '项目解析'},
            {'role': 'user', 'content': json.dumps({'skill': ANALYSIS_SKILL})}]


async def ignore_event(*args):
    pass


async def test_server_ignoring_parallel_false_can_read_two_files_with_correct_native_round_trip():
    calls = [native(0, path='main.py'), native(1, path='README.md')]
    with streaming_model(calls) as s:
        raw = await s.model.generate(MESSAGES, ignore_event)
        batch = parse_action(raw)
        assert batch['action'] == 'read_batch' and len(batch['args']['actions']) == 2
        assert s.model.last_tool_call is None
        assert s.model.last_tool_calls == calls
        results = [{'tool_call_id': call['id'], 'result': {'path': path, 'content': text}}
                   for call, path, text in zip(calls, ['main.py', 'README.md'], ['value = 1\n', '# 项目\n'])]
        history = [*MESSAGES, {'role': 'assistant', 'content': raw, 'tool_calls': calls},
                   {'role': 'user', 'content': '工具观察：' + json.dumps({'tool_results': results}, ensure_ascii=False)}]
        await s.model.generate(history, ignore_event)
        wire = s.requests[1]['messages']
        assert [item['tool_call_id'] for item in wire if item['role'] == 'tool'] == [call['id'] for call in calls]
        assert [json.loads(item['content']) for item in wire if item['role'] == 'tool'] == [item['result'] for item in results]
        assert wire[-3]['tool_calls'] == calls
        assert 'fabricated tool observation' not in json.dumps(wire)
        assert all(request['parallel_tool_calls'] is False for request in s.requests)


@pytest.mark.parametrize('action', ['propose_patch', 'propose_documentation', 'test', 'final', 'read_batch'])
async def test_native_batch_with_any_non_read_action_is_rejected_before_execution(action):
    calls = [native(0, path='main.py'), native(1, action)]
    with streaming_model(calls) as s:
        with pytest.raises(ActionFormatError, match='只能全部为只读'):
            await s.model.generate(MESSAGES, ignore_event)
        assert not s.model.last_tool_calls and s.model.llm.last_tool_call is None


@pytest.mark.parametrize('corruption', ['duplicate_id', 'unknown_function', 'incomplete', 'too_many', 'truncated'])
async def test_native_batch_invalid_or_truncated_response_never_becomes_accepted_calls(corruption):
    calls = [native(0, path='main.py'), native(1, path='README.md')]
    if corruption == 'duplicate_id': calls[1]['id'] = calls[0]['id']
    elif corruption == 'unknown_function': calls[1]['function']['name'] = 'unknown_tool'
    elif corruption == 'incomplete': calls[1]['function']['arguments'] = '{"action":"read","args":'
    elif corruption == 'too_many': calls = [native(index, path='main.py') for index in range(17)]
    with streaming_model(calls, 'length' if corruption == 'truncated' else 'tool_calls') as s:
        with pytest.raises(ModelOutputTruncated if corruption == 'truncated' else ActionFormatError):
            await s.model.generate(MESSAGES, ignore_event)
        assert not s.model.last_tool_calls


def test_unpaired_native_batch_history_cannot_emit_dangling_or_invented_tool_ids():
    calls = [native(0, path='main.py'), native(1, path='README.md')]
    messages = [{'role': 'assistant', 'content': json.dumps(native_read_batch(calls)), 'tool_calls': calls},
                {'role': 'user', 'content': '工具观察：' + json.dumps({'tool_results': [
                    {'tool_call_id': 'invented-id', 'result': 'not a real result'}]})}]
    wire = tool_messages(messages)
    assert not any(item.get('tool_calls') or item['role'] == 'tool' for item in wire)


def test_native_read_batch_can_hold_sixteen_independent_calls_without_a_single_call_limit():
    calls = [native(index, path=f'module_{index}.py') for index in range(16)]
    assert len(native_read_batch(calls)['args']['actions']) == 16


@pytest.mark.parametrize('metadata', ['repeat', 'cumulative', 'fragment'])
async def test_streamed_tool_identity_is_not_duplicated(metadata):
    calls = [native(0, path='main.py'), native(1, path='README.md')]
    with streaming_model(calls, metadata=metadata) as s:
        batch = parse_action(await s.model.generate(MESSAGES, ignore_event))
        assert batch['action'] == 'read_batch'
        assert s.model.last_tool_calls == calls


@pytest.mark.parametrize('fault', ['missing_id', 'wrong_name'])
async def test_protocol_errors_record_redacted_metadata_and_distinct_failure_reasons(fault):
    call = native(0, path='argument-content-must-not-appear-in-diagnostics')
    if fault == 'missing_id': call['id'] = ''
    else: call['function']['name'] = 'unknown_gateway_function'
    events = []
    async def emit(kind, data):
        events.append((kind, data))
    with streaming_model([call]) as s:
        with pytest.raises(ModelProtocolError, match='ID' if fault == 'missing_id' else '工具名不匹配'):
            await s.model.generate(MESSAGES, emit)
    diagnostics = [data for kind, data in events if kind == 'model.protocol_diagnostic']
    assert diagnostics and diagnostics[0]['code'] == ('missing_call_id' if fault == 'missing_id' else 'tool_name_mismatch')
    assert diagnostics[0]['expected_tool'] == 'submit_action'
    assert 'argument-content-must-not-appear-in-diagnostics' not in json.dumps(diagnostics)
    assert call['id'] == '' or call['id'] not in json.dumps(diagnostics)
