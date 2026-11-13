"""Staged comments preserve source and resume without carrying full-file context."""
from __future__ import annotations

import ast
import json

import pytest

from backend.annotation_drafts import AnnotationDrafts, UNIT_CHARS, encoded_size
from backend.skills import validate_annotation_change
from backend.store import Store, identifier, now
from backend.workspace import Conflict, Workspace, digest


@pytest.fixture
def service(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    store = Store(tmp_path / 'service/state.sqlite3')
    workspace_id, session_id, task_id = identifier(), identifier(), identifier()
    store.execute('INSERT INTO workspaces VALUES(?,?,?)', (workspace_id, str(root), 'workspace'))
    store.execute('INSERT INTO sessions VALUES(?,?,?,?)', (session_id, workspace_id, 'annotation', now()))
    store.execute('INSERT INTO tasks(id,session_id,workspace_id,prompt,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                  (task_id, session_id, workspace_id, '注释', 'running', now(), now()))
    workspace = Workspace(str(root))
    return root, store, task_id, workspace


def document(unit):
    if unit['kind'] == 'header':
        return {'purpose': '提供示例计算与调用接口。', 'input_files': '无。', 'inputs': '由调用方传入内存参数。',
                'output_files': '无。', 'outputs': '返回对应函数的计算结果。'}
    return {'purpose': '执行该函数的示例计算并返回结果。',
            'inputs': '；'.join(f'{p}：调用方提供的参数。' for p in unit['parameters']) or '无。',
            'outputs': '返回函数计算得到的结果。'}


def complete(drafts, path='sample.py'):
    units = []
    while True:
        unit = drafts.prepare(path)
        if unit['ready']:
            return units
        units.append(unit)
        result = drafts.stage(path, unit['base_hash'], unit['target_id'], document(unit))
        assert result['progress']['done'] == len(units)


def test_large_fifteen_function_file_uses_small_exact_units_and_one_checked_candidate(service):
    root, store, task_id, workspace = service
    before = ''.join(f'value_{index} = {index}\n' for index in range(3200))
    before += '\n'.join(f'def function_{index}(value):\n    return value + {index}\n' for index in range(15))
    assert len(before) > 51000
    (root / 'sample.py').write_bytes(before.encode())
    drafts = AnnotationDrafts(store, task_id, workspace)
    units = complete(drafts)
    assert len(units) == 16
    assert units[0]['source_is_overview'] is True
    assert all(encoded_size(unit) <= UNIT_CHARS for unit in units)
    assert all(not unit['source_is_overview'] and unit['source'].startswith('def ') for unit in units[1:])
    candidate = drafts.candidate('sample.py')
    assert candidate['base_hash'] == digest(before) and candidate['before'] == before
    assert ast.dump(ast.parse(candidate['after'])) == ast.dump(ast.parse(before))
    assert validate_annotation_change('sample.py', before, candidate['after'])['functions'] == 15
    assert (root / 'sample.py').read_bytes() == before.encode(), 'drafts never partially write files'


def test_drafts_resume_across_instances_without_repeating_saved_header(service):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'def add(a, b):\n    return a + b\n')
    first = AnnotationDrafts(store, task_id, workspace)
    header = first.prepare('sample.py')
    first.stage('sample.py', header['base_hash'], header['target_id'], document(header))
    second = AnnotationDrafts(store, task_id, workspace)
    unit = second.prepare('sample.py')
    assert unit['kind'] == 'function' and unit['progress'] == {'done': 1, 'total': 2}
    assert unit['parameters'] == ['a', 'b']
    with pytest.raises(Conflict):
        first.stage('sample.py', header['base_hash'], unit['target_id'], document(unit))
    assert second.summary('sample.py')['progress']['done'] == 1


@pytest.mark.parametrize('field', ['purpose', 'inputs', 'outputs'])
def test_missing_fields_rejected_without_advancing(service, field):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'def add(a):\n    return a\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    unit = drafts.prepare('sample.py')
    invalid = document(unit)
    invalid.pop(field)
    with pytest.raises(ValueError, match='字段'):
        drafts.stage('sample.py', unit['base_hash'], unit['target_id'], invalid)
    assert drafts.prepare('sample.py')['progress']['done'] == 0


def test_parameters_no_args_and_wrong_target_are_checked(service):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'def collect(self, /, value, *args, flag=None, **kwargs):\n    return value\n\ndef empty():\n    return None\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    header = drafts.prepare('sample.py')
    with pytest.raises(ValueError, match='target_id'):
        drafts.stage('sample.py', header['base_hash'], 'fake', document(header))
    drafts.stage('sample.py', header['base_hash'], header['target_id'], document(header))
    fn = drafts.prepare('sample.py')
    invalid = document(fn)
    invalid['inputs'] = 'value：仅此参数。'
    with pytest.raises(ValueError, match='self'):
        drafts.stage('sample.py', fn['base_hash'], fn['target_id'], invalid)
    drafts.stage('sample.py', fn['base_hash'], fn['target_id'], document(fn))
    empty = drafts.prepare('sample.py')
    invalid = document(empty)
    invalid['inputs'] = '参数不存在。'
    with pytest.raises(ValueError, match='无参数'):
        drafts.stage('sample.py', empty['base_hash'], empty['target_id'], invalid)


def test_external_edit_discards_old_draft_and_candidate_refuses_old_baseline(service):
    root, store, task_id, workspace = service
    source = root / 'sample.py'
    source.write_bytes(b'def add(a):\n    return a\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    complete(drafts)
    before = drafts.candidate('sample.py')
    source.write_bytes(b'def add(a):\n    return a + 1\n')
    with pytest.raises(Conflict, match='基线'):
        drafts.candidate('sample.py')
    unit = drafts.prepare('sample.py')
    assert unit['reset'] and unit['progress']['done'] == 0
    assert unit['base_hash'] != before['base_hash']


def test_candidate_requires_all_units_and_finished_drafts_are_not_replayed(service):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'def add(a):\n    return a\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    drafts.prepare('sample.py')
    with pytest.raises(ValueError, match='尚未覆盖'):
        drafts.candidate('sample.py')
    complete(drafts)
    drafts.finish('sample.py')
    assert drafts.prepare('sample.py')['progress']['done'] == 0


def test_old_reverted_patch_resets_ready_draft_only_once(service):
    root, store, task_id, workspace = service
    content = 'def add(a):\n    return a\n'
    (root / 'sample.py').write_bytes(content.encode())
    drafts = AnnotationDrafts(store, task_id, workspace)
    complete(drafts)
    store.execute('INSERT INTO patches VALUES(?,?,?,?,?,?)',
                  (identifier(), task_id, store.one('tasks', task_id)['workspace_id'], 'reverted',
                   json.dumps([{'path': 'sample.py', 'before_hash': digest(content)}]), now()))
    header = drafts.prepare('sample.py')
    assert header['reset'] and header['progress']['done'] == 0
    drafts.stage('sample.py', header['base_hash'], header['target_id'], document(header))
    assert drafts.prepare('sample.py')['kind'] == 'function'


@pytest.mark.parametrize('newline', ['\n', '\r\n'], ids=['lf', 'crlf'])
def test_bom_shebang_encoding_docstrings_nested_decorators_and_old_comments_are_preserved(service, newline):
    root, store, task_id, workspace = service
    lines = ['#!/usr/bin/env python', '# coding: utf-8', '# Copyright original license',
             '# 代码用途：旧用途。', '# 输入文件：无。', '# 输入说明：旧。', '# 输出文件：无。', '# 输出说明：旧。',
             '"""Module documentation.', '# 函数用途：This is string data, not a comment.', '"""',
             'def decorate(fn):', '    return fn', '', '# 函数用途：旧。', '# 输入说明：value：旧。', '# 输出说明：旧。',
             '@decorate', 'def outer(value):', '    """Keep this function documentation."""',
             '    # 函数用途：旧嵌套。', '    # 输入说明：x：旧。', '    # 输出说明：旧。',
             '    def inner(x):', '        return x', '    return inner(value)', '']
    content = '\ufeff' + newline.join(lines)
    (root / 'sample.py').write_bytes(content.encode())
    drafts = AnnotationDrafts(store, task_id, workspace)
    units = complete(drafts)
    assert [unit['name'] for unit in units] == ['文件头', 'decorate', 'outer', 'outer.inner']
    candidate = drafts.candidate('sample.py')
    assert candidate['after'].startswith('\ufeff#!/usr/bin/env python' + newline + '# coding: utf-8' + newline)
    assert '# Copyright original license' + newline in candidate['after']
    assert '# 函数用途：This is string data, not a comment.' in candidate['after']
    assert '    # 函数用途：执行该函数' in candidate['after']
    assert '旧用途' not in candidate['after'] and '旧嵌套' not in candidate['after']
    if newline == '\r\n':
        assert '\n' not in candidate['after'].replace('\r\n', '')


@pytest.mark.parametrize('value', ['说明\n# fmt: off', '说明\n函数用途：伪造字段', '说明\n# type: ignore'])
def test_metadata_and_control_injection_rejected(service, value):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'value = 1\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    unit = drafts.prepare('sample.py')
    invalid = document(unit)
    invalid['purpose'] = value
    with pytest.raises(ValueError, match='注入'):
        drafts.stage('sample.py', unit['base_hash'], unit['target_id'], invalid)


def test_oversized_single_function_reports_block_without_inventing_source(service):
    root, store, task_id, workspace = service
    source = 'def huge(value):\n' + ''.join(f'    value += {number}\n' for number in range(1800)) + '    return value\n'
    (root / 'sample.py').write_bytes(source.encode())
    drafts = AnnotationDrafts(store, task_id, workspace)
    header = drafts.prepare('sample.py')
    drafts.stage('sample.py', header['base_hash'], header['target_id'], document(header))
    with pytest.raises(ValueError, match='单函数上下文超过'):
        drafts.prepare('sample.py')
    assert (root / 'sample.py').read_bytes() == source.encode()


def test_delete_clears_drafts_and_late_worker_cannot_revive_records(service):
    root, store, task_id, workspace = service
    (root / 'sample.py').write_bytes(b'value = 1\n')
    drafts = AnnotationDrafts(store, task_id, workspace)
    unit = drafts.prepare('sample.py')
    store.delete_task(task_id)
    with pytest.raises(Conflict):
        drafts.stage('sample.py', unit['base_hash'], unit['target_id'], document(unit))
    assert store.rows('SELECT * FROM annotation_drafts') == []
    assert store.rows('SELECT * FROM annotation_draft_owners') == []
