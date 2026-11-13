"""Patch validation must report repairable fields and preserve review boundaries."""
from __future__ import annotations

import json

import pytest

from backend.patches import Patches
from backend.runtime import Runtime
from backend.settings import Settings
from backend.skills import ANNOTATION_SKILL, annotation_read_hints, load_skill
from backend.store import Store, identifier, now
from backend.workspace import digest


DOCUMENTATION = '"""Start the local service.\nKeep this module documentation.\n"""\n'
PREFIX = '#!/usr/bin/env python3\n' + DOCUMENTATION
IMPORT = 'from __future__ import annotations\n\n'
FUNCTION = 'def run(port=8000):\n    return port\n'
BEFORE = PREFIX + IMPORT + FUNCTION
HEADER = (
    '# 代码用途：提供服务端口的入口配置。\n'
    '# 输入文件：无。\n'
    '# 输入说明：调用方传入服务端口。\n'
    '# 输出文件：无。\n'
    '# 输出说明：返回服务端口，不写入文件。\n'
)
FUNCTION_COMMENT = (
    '# 函数用途：返回调用方指定的服务端口。\n'
    '# 输入说明：port：服务端口，默认 8000。\n'
    '# 输出说明：返回 port 的原值。\n'
)
AFTER = PREFIX + HEADER + IMPORT + FUNCTION_COMMENT + FUNCTION


@pytest.fixture
def annotation_workspace(tmp_path):
    root = tmp_path / 'workspace'
    (root / 'backend').mkdir(parents=True)
    source = root / 'backend/run.py'
    source.write_text(BEFORE, encoding='utf-8', newline='')
    store = Store(tmp_path / 'data/state.sqlite3')
    workspace_id, task_id = identifier(), identifier()
    store.execute('INSERT INTO workspaces VALUES(?,?,?)', (workspace_id, str(root), 'workspace'))
    store.execute(
        'INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,skill_instructions,created_at,updated_at) '
        'VALUES(?,?,?,?,?,?,?,?,?)',
        (task_id, identifier(), workspace_id, '添加中文注释', 'queued', ANNOTATION_SKILL,
         load_skill(ANNOTATION_SKILL), now(), now()),
    )
    return store, store.one('tasks', task_id), source


@pytest.mark.parametrize('changes,required_message', [
    (None, 'changes'),
    ({'path': 'backend/run.py'}, 'changes'),
    ([None], 'changes[0]'),
    ([{}], 'changes[0].path'),
    ([{'path': '  '}], 'changes[0].path'),
    ([{'path': 'backend/run.py'}], 'changes[0].base_hash'),
    ([{'path': 'backend/run.py', 'base_hash': 123}], 'changes[0].base_hash'),
])
def test_bad_patch_shape_reports_the_field_without_creating_a_checkpoint(annotation_workspace, changes, required_message):
    store, task, source = annotation_workspace
    with pytest.raises(ValueError) as caught:
        Patches(store).propose(task, changes)
    assert required_message in str(caught.value)
    assert store.rows('SELECT id FROM patches') == []
    assert source.read_bytes() == BEFORE.encode('utf-8')


def test_bad_second_change_does_not_persist_a_partially_prepared_patch(annotation_workspace):
    store, task, source = annotation_workspace
    changes = [
        {'path': 'backend/run.py', 'base_hash': digest(BEFORE), 'content': AFTER},
        {'base_hash': digest(BEFORE), 'content': AFTER},
    ]
    with pytest.raises(ValueError, match=r'changes\[1\]\.path'):
        Patches(store).propose(task, changes)
    assert store.rows('SELECT id FROM patches') == []
    assert source.read_bytes() == BEFORE.encode('utf-8')


def test_corrected_docstring_header_edits_can_be_reviewed_applied_and_undone(annotation_workspace):
    store, task, source = annotation_workspace
    patches = Patches(store)
    # A header after an import is invalid; rejecting it must leave the same
    # baseline available for a corrected patch without a phantom checkpoint.
    wrong_location = PREFIX + IMPORT + HEADER + FUNCTION_COMMENT + FUNCTION
    with pytest.raises(ValueError, match='五项文件头'):
        patches.propose(task, [{'path': 'backend/run.py', 'base_hash': digest(BEFORE), 'content': wrong_location}])
    assert store.rows('SELECT id FROM patches') == []
    assert source.read_bytes() == BEFORE.encode('utf-8')

    patch = patches.propose(task, [{'path': 'backend/run.py', 'base_hash': digest(BEFORE), 'edits': [
        {'old': IMPORT, 'new': HEADER + IMPORT},
        {'old': 'def run(port=8000):', 'new': FUNCTION_COMMENT + 'def run(port=8000):'},
    ]}])
    assert patch['status'] == 'proposed'
    assert patch['changes'][0]['before_hash'] == digest(BEFORE)
    assert patch['changes'][0]['after'] == AFTER
    assert '+# 代码用途：' in patch['changes'][0]['diff']
    assert source.read_bytes() == BEFORE.encode('utf-8')

    assert patches.apply(patch['id'])['status'] == 'applied'
    assert source.read_bytes() == AFTER.encode('utf-8')
    assert patches.apply(patch['id'], undo=True)['status'] == 'reverted'
    assert source.read_bytes() == BEFORE.encode('utf-8')


def test_annotation_read_hints_report_real_docstring_and_header_positions():
    hints = annotation_read_hints('backend/run.py', BEFORE)
    assert hints['module_docstring_end_line'] == 4
    assert hints['first_code_line'] == 5
    assert hints['detected_fields'] == []
    annotated_hints = annotation_read_hints('backend/run.py', AFTER)
    assert annotated_hints['module_docstring_end_line'] == 4
    assert annotated_hints['first_code_line'] == 10
    assert annotated_hints['detected_fields'] == annotated_hints['required_fields']
    assert 'shebang' in annotated_hints['note']
    assert annotation_read_hints('frontend/main.ts', 'export const value = 1;') is None


async def test_annotation_read_delivers_position_hints_with_real_content_and_hash(annotation_workspace):
    store, task, source = annotation_workspace
    seen = []

    class ReadThenFinishModel:
        async def generate(self, messages, emit):
            seen.append(messages)
            if len(seen) == 1:
                action = {'action': 'read', 'args': {'path': 'backend/run.py'}, 'summary': '读取入口源码'}
            else:
                action = {'action': 'final', 'args': {'message': '仅完成读取，尚未修改源码。'}, 'summary': '结束读取测试'}
            return json.dumps(action, ensure_ascii=False)

        def close(self):
            pass

    runtime = Runtime(store, Settings(store, persist_secrets=False), ReadThenFinishModel)
    try:
        await runtime.run(task['id'])
        assert store.one('tasks', task['id'])['status'] == 'completed'
        observation = json.loads(seen[1][-1]['content'].removeprefix('工具观察：'))
        assert observation['path'] == 'backend/run.py'
        assert observation['content'] == BEFORE
        assert observation['hash'] == digest(BEFORE)
        expected_hints = annotation_read_hints('backend/run.py', BEFORE)
        assert {key: observation['annotation_format'][key] for key in expected_hints} == expected_hints
        assert observation['annotation_format']['positions_truncated'] is False
        assert observation['start_line'] == 1 and observation['next_start_line'] is None
        assert store.rows('SELECT id FROM patches') == []
        assert source.read_bytes() == BEFORE.encode('utf-8')
    finally:
        await runtime.close()
