"""Recover deterministic annotation packaging errors without guessing code."""
from __future__ import annotations

import json

import pytest

from backend.patches import AnnotationAlreadyComplete, EditMatchError, Patches
from backend.runtime import Runtime
from backend.settings import Settings
from backend.skills import ANNOTATION_SKILL, load_skill, validate_annotation_change
from backend.store import Store, identifier, now
from backend.workspace import Conflict, digest


HEADER = ('# 代码用途：提供参数回传工具。\n# 输入文件：无。\n# 输入说明：调用方传入参数。\n'
          '# 输出文件：无。\n# 输出说明：返回传入的参数。\n')
COMMENT = ('# 函数用途：返回传入的参数。\n# 输入说明：self：当前实例；parameters：传入的参数。\n'
           '# 输出说明：原样返回 parameters。\n')
UPDATED = COMMENT.replace('原样返回 parameters', '返回调用方传入的 parameters 参数')
BEFORE = HEADER + 'class Tool:\n' + ''.join('    ' + line for line in COMMENT.splitlines(keepends=True)) + '    def execute(self, parameters):\n        return parameters\n'
AFTER = BEFORE.replace('原样返回 parameters', '返回调用方传入的 parameters 参数')


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    source = root / 'tool.py'
    source.write_bytes(BEFORE.encode())
    store = Store(tmp_path / 'state.sqlite3')
    workspace_id, task_id = identifier(), identifier()
    store.execute('INSERT INTO workspaces VALUES(?,?,?)', (workspace_id, str(root), 'workspace'))
    store.execute('INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,skill_instructions,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                  (task_id, identifier(), workspace_id, '为项目补充注释', 'queued', ANNOTATION_SKILL,
                   load_skill(ANNOTATION_SKILL), now(), now()))
    return store, store.one('tasks', task_id), source


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
@pytest.mark.parametrize('indent', ['    ', '\t'])
@pytest.mark.parametrize('with_code_context', [False, True])
def test_dropped_comment_indentation_and_line_endings_are_restored_uniquely(newline, indent, with_code_context):
    before = BEFORE.replace('    ', indent).replace('\n', newline)
    after = AFTER.replace('    ', indent).replace('\n', newline)
    diagnostics = []
    context = indent + 'def execute(self, parameters):' if with_code_context else ''
    old = COMMENT + context if with_code_context else COMMENT.rstrip('\n')
    new = UPDATED + context if with_code_context else UPDATED.rstrip('\n')
    result = Patches.apply_edits(before, [{'old': old, 'new': new}],
                                 recover_comments=True, diagnostics=diagnostics)
    assert result == after and len(diagnostics) == 1
    validate_annotation_change('tool.py', before, result)


@pytest.mark.parametrize('before,old,new', [
    ('    # same\n    # block\n        # same\n        # block\n', '# same\n# block', '# new\n# text'),
    ('# same\n    # same\n', '# same', '# new'),
    ('    def method():\n        pass\n', 'def method():\n    pass', '# 注释\ndef method():\n    pass'),
    ('    # actual\n    # text\n', '# typo\n# text', '# replacement'),
])
def test_ambiguous_comments_code_indentation_and_text_typos_are_not_guessed(before, old, new):
    with pytest.raises(EditMatchError, match=r'edits\[0\]'):
        Patches.apply_edits(before, [{'old': old, 'new': new}], recover_comments=True)


def test_annotation_newline_recovery_preserves_actual_file_bytes():
    before = 'import os\r\nimport sys\r\n'
    edits = [{'old': 'import os\nimport sys\n', 'new': '# 说明\nimport os\nimport sys\n'}]
    assert Patches.apply_edits(before, edits, recover_comments=True) == '# 说明\r\n' + before
    with pytest.raises(EditMatchError):
        Patches.apply_edits(before, edits)  # General code changes remain strict.


def test_recovered_comment_patch_still_checks_logic_and_can_apply_and_undo(workspace):
    store, task, source = workspace
    patches, diagnostics = Patches(store), []
    patch = patches.propose(task, [{'path': 'tool.py', 'base_hash': digest(BEFORE), 'edits': [
        {'old': COMMENT.rstrip('\n'), 'new': UPDATED.rstrip('\n')}]}], diagnostics=diagnostics)
    assert diagnostics and source.read_bytes() == BEFORE.encode()
    patches.apply(patch['id'])
    assert source.read_bytes() == AFTER.encode()
    patches.apply(patch['id'], undo=True)
    assert source.read_bytes() == BEFORE.encode()
    with pytest.raises(ValueError, match='代码|排版'):
        patches.propose(task, [{'path': 'tool.py', 'base_hash': digest(BEFORE), 'edits': [
            {'old': COMMENT.rstrip('\n'), 'new': UPDATED.rstrip('\n')},
            {'old': 'return parameters', 'new': 'return None'}]}])


def test_missing_path_requires_one_real_read_hash_and_a_current_baseline(workspace):
    store, task, source = workspace
    patches = Patches(store)
    change = {'base_hash': digest(BEFORE), 'content': AFTER}
    with pytest.raises(ValueError, match='path'):
        patches.propose(task, [change])
    (source.parent / 'duplicate.py').write_bytes(BEFORE.encode())
    with pytest.raises(ValueError, match='path'):
        patches.propose(task, [change], read_baselines={'tool.py': digest(BEFORE), 'duplicate.py': digest(BEFORE)})
    diagnostics = []
    patch = patches.propose(task, [change], read_baselines={'tool.py': digest(BEFORE)}, diagnostics=diagnostics)
    assert patch['changes'][0]['path'] == 'tool.py' and diagnostics
    assert 'path' not in change  # Do not mutate provider arguments.
    source.write_bytes((BEFORE + '# external\n').encode())
    with pytest.raises((Conflict, ValueError)):
        patches.propose(task, [change], read_baselines={'tool.py': digest(BEFORE)})
    with pytest.raises(Conflict):
        patches.apply(patch['id'])


def test_no_change_is_only_success_when_annotation_coverage_already_passes(workspace):
    store, task, source = workspace
    patches = Patches(store)
    with pytest.raises(AnnotationAlreadyComplete):
        patches.propose(task, [{'path': 'tool.py', 'base_hash': digest(BEFORE), 'content': BEFORE}])
    assert not store.rows('SELECT id FROM patches')
    incomplete = 'value = 1\n'
    source.write_bytes(incomplete.encode())
    with pytest.raises(ValueError, match='五项文件头'):
        patches.propose(task, [{'path': 'tool.py', 'base_hash': digest(incomplete), 'content': incomplete}])


def test_no_change_file_does_not_block_other_valid_files_in_same_batch(workspace):
    store, task, source = workspace
    other = source.parent / 'other.py'
    other.write_bytes(BEFORE.encode())
    patch = Patches(store).propose(task, [
        {'path': 'tool.py', 'base_hash': digest(BEFORE), 'content': BEFORE},
        {'path': 'other.py', 'base_hash': digest(BEFORE), 'content': AFTER}])
    assert [change['path'] for change in patch['changes']] == ['other.py']


@pytest.mark.parametrize('invalid_first', [False, True])
async def test_runtime_repairs_comments_and_missing_paths_and_advances_past_noops(workspace, invalid_first):
    store, task, source = workspace
    responses = [{'action': 'read', 'args': {'path': 'tool.py'}}]
    if invalid_first:
        responses.append({'action': 'propose_patch', 'args': {'changes': [{'path': 'tool.py', 'base_hash': digest(BEFORE),
            'edits': [{'old': '# not the actual comment', 'new': '# replacement'}]}]}})
    responses += [
        {'action': 'propose_patch', 'args': {'changes': [{'base_hash': digest(BEFORE),
            'edits': [{'old': COMMENT.rstrip('\n'), 'new': UPDATED.rstrip('\n')}]}]}},
        {'action': 'propose_patch', 'args': {'changes': [{'path': 'tool.py', 'base_hash': digest(AFTER), 'content': AFTER}]}},
        {'action': 'final', 'args': {'message': '注释已完成。'}}]
    seen = []
    class Model:
        async def generate(self, messages, emit):
            seen.append(messages)
            return json.dumps(responses.pop(0))
        def close(self):
            pass
    runtime = Runtime(store, Settings(store, persist_secrets=False), Model)
    try:
        await runtime.run(task['id'])
        assert store.one('tasks', task['id'])['status'] == 'completed'
        assert source.read_bytes() == AFTER.encode()
        events = store.events(task['id'])
        assert len([e for e in events if e['kind'] == 'patch.applied']) == 1
        assert len([e for e in events if e['kind'] == 'patch.unchanged']) == 1
        assert any(e['kind'] == 'patch.normalized' and '路径' in e['data']['message'] for e in events)
        assert len(store.rows('SELECT id FROM patches')) == 1
        if invalid_first:
            feedback = seen[2][-1]['content']
            assert 'edits[0]' in feedback and '当前真实读取结果' in feedback
            current = json.loads(feedback.removeprefix('工具观察：'))['recovery']['current_read']
            assert current['hash'] == digest(BEFORE) and current['content'] == BEFORE
        else:
            assert not any(e['kind'] == 'tool.error' for e in events)
    finally:
        await runtime.close()
