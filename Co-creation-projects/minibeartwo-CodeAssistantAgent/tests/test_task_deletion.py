"""History deletion is atomic and never rolls back project files."""
from __future__ import annotations

import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.store import identifier, now
from backend.workspace import digest


AUTH = {'Authorization': 'Bearer history-test'}


@pytest.fixture
def history(tmp_path):
    app = create_app(tmp_path / 'service', token='history-test', persist_secrets=False)
    root = tmp_path / 'workspace'
    root.mkdir()
    store = app.state.store
    workspace_id, session_id = identifier(), identifier()
    store.execute('INSERT INTO workspaces VALUES(?,?,?)', (workspace_id, str(root), 'workspace'))
    store.execute('INSERT INTO sessions VALUES(?,?,?,?)', (session_id, workspace_id, 'session', now()))
    def task(status='completed'):
        task_id = identifier()
        store.execute('INSERT INTO tasks(id,session_id,workspace_id,prompt,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                      (task_id, session_id, workspace_id, '历史任务', status, now(), now()))
        return task_id
    return app, root, workspace_id, session_id, task


def test_delete_history_removes_events_and_diffs_but_preserves_applied_files(history):
    app, root, workspace_id, session_id, create_task = history
    task_id = create_task()
    source = root / 'example.txt'
    source.write_bytes(b'before\n')
    patches, store = app.state.runtime.patches, app.state.store
    patch = patches.propose(store.one('tasks', task_id), [{'path': 'example.txt', 'base_hash': digest('before\n'), 'content': 'after\n'}])
    patches.apply(patch['id'])
    store.event(task_id, 'patch.applied', {'patch_id': patch['id']})
    with TestClient(app, headers=AUTH) as client:
        assert client.delete(f'/api/tasks/{task_id}', headers={'Authorization': 'wrong'}).status_code == 401
        response = client.delete(f'/api/tasks/{task_id}')
        assert response.status_code == 200 and response.json() == {'id': task_id, 'deleted': True}
        assert source.read_bytes() == b'after\n'
        assert client.get(f'/api/tasks/{task_id}').status_code == 404
        assert client.get(f'/api/tasks/{task_id}/events').status_code == 404
        assert client.post(f"/api/patches/{patch['id']}/undo").status_code == 404
        assert client.delete(f'/api/tasks/{task_id}').status_code == 404
        assert not store.rows('SELECT * FROM events WHERE task_id=?', (task_id,))
        assert not store.rows('SELECT * FROM patches WHERE task_id=?', (task_id,))
        assert not store.rows('SELECT * FROM sessions WHERE id=?', (session_id,))
        assert store.one('workspaces', workspace_id)['root'] == str(root)
    restarted = create_app(store.path.parent, token='history-test', persist_secrets=False)
    with TestClient(restarted, headers=AUTH) as client:
        assert client.get('/api/sessions', params={'workspace_id': workspace_id}).json() == []
        assert client.get(f'/api/tasks/{task_id}').status_code == 404
        assert source.read_bytes() == b'after\n'


@pytest.mark.parametrize('status', ['running', 'queued', 'cancelling', 'waiting_review'])
def test_unfinished_tasks_must_be_stopped_before_deletion(history, status):
    app, _, _, _, create_task = history
    with TestClient(app, headers=AUTH) as client:
        task_id = create_task(status)  # Seed after startup recovery.
        app.state.store.event(task_id, 'agent.activity', {'message': '保持活动记录'})
        response = client.delete(f'/api/tasks/{task_id}')
        assert response.status_code == 409 and '先停止' in response.json()['detail']
        assert app.state.store.one('tasks', task_id)['status'] == status
        assert app.state.store.events(task_id)
        assert client.post(f'/api/tasks/{task_id}/cancel').status_code == 200
        assert client.delete(f'/api/tasks/{task_id}').status_code == 200


def test_deleting_one_task_preserves_other_tasks_in_the_session(history):
    app, _, _, session_id, create_task = history
    first, second = create_task(), create_task('cancelled')
    with TestClient(app, headers=AUTH) as client:
        assert client.delete(f'/api/tasks/{first}').status_code == 200
        remaining = client.get(f'/api/sessions/{session_id}/tasks').json()
        assert [item['id'] for item in remaining] == [second]
        assert client.delete(f'/api/tasks/{second}').status_code == 200
        assert client.get(f'/api/sessions/{session_id}/tasks').status_code == 404


def test_recovery_checkpoint_cannot_be_deleted_before_recovery(history):
    app, root, _, _, create_task = history
    task_id = create_task('interrupted')
    source = root / 'example.txt'
    source.write_bytes(b'before\n')
    patches, store = app.state.runtime.patches, app.state.store
    patch = patches.propose(store.one('tasks', task_id), [{'path': 'example.txt', 'base_hash': digest('before\n'), 'content': 'after\n'}])
    store.execute("UPDATE patches SET status='recovery_required' WHERE id=?", (patch['id'],))
    with TestClient(app, headers=AUTH) as client:
        response = client.delete(f'/api/tasks/{task_id}')
        assert response.status_code == 409 and '恢复' in response.json()['detail']
        assert store.one('tasks', task_id) and patches.get(patch['id'])['status'] == 'recovery_required'


def test_history_deletion_rolls_back_all_records_if_transaction_fails(history):
    app, _, _, session_id, create_task = history
    store = app.state.store
    task_id = create_task()
    store.event(task_id, 'task.completed', {'message': '完成'})
    store.execute("CREATE TRIGGER block_history_delete BEFORE DELETE ON tasks BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.delete_task(task_id)
    assert store.one('tasks', task_id) and store.one('sessions', session_id)
    assert len(store.events(task_id)) == 1


def test_task_can_be_stopped_and_deleted_while_framework_initializes(history, monkeypatch):
    app, _, workspace_id, _, _ = history
    entered, release = threading.Event(), threading.Event()
    def slow_registry():
        entered.set()
        release.wait(10)
        return None  # Cancellation must finish before the registry is used.
    monkeypatch.setattr('backend.runtime.create_tool_registry', slow_registry)
    with TestClient(app, headers=AUTH) as client:
        try:
            response = client.post('/api/tasks', json={'workspace_id': workspace_id, 'prompt': '读取项目'})
            assert response.status_code == 202
            task_id = response.json()['id']
            assert entered.wait(2)
            assert client.get(f'/api/tasks/{task_id}').json()['status'] == 'running'
            assert client.post(f'/api/tasks/{task_id}/cancel').json()['status'] == 'cancelled'
            assert client.delete(f'/api/tasks/{task_id}').status_code == 200
            assert not release.is_set()
        finally:
            release.set()
