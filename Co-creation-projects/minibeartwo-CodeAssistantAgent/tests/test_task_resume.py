"""Explicit annotation continuation preserves identity, evidence and lifecycle."""
from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.model import tool_messages
from backend.runtime import SYSTEM
from backend.skills import ANNOTATION_SKILL, load_skill
from backend.store import identifier, now
from backend.workspace import digest


AUTH = {"Authorization": "Bearer resume-test"}
BEFORE = "value = 1\n"
AFTER = ("# 代码用途：定义示例数值。\n# 输入文件：无。\n# 输入说明：无外部输入。\n"
         "# 输出文件：无。\n# 输出说明：提供 value 数值。\n" + BEFORE)


def action(name, **args):
    return json.dumps({"action": name, "args": args, "summary": name}, ensure_ascii=False)


class Registry:
    def __init__(self):
        self.functions = {}

    def register_function(self, name, description, function):
        self.functions[name] = function

    def execute_tool(self, name, args):
        return self.functions[name](args)


class ScriptedModel:
    def __init__(self, script, seen, settings):
        self.script, self.seen, self.settings = script, seen, settings
        self.closed = False

    async def generate(self, messages, emit):
        self.seen.append(messages)
        response = self.script.popleft()
        if isinstance(response, Exception):
            raise response
        if response == "wait":
            await asyncio.Event().wait()
        return response(messages) if callable(response) else response

    def close(self):
        self.closed = True


def wait_task(client, task_id, status, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = client.get(f"/api/tasks/{task_id}").json()
        if task["status"] == status:
            return task
        time.sleep(.01)
    pytest.fail(f"Expected {status}, got {task}")


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.runtime.create_tool_registry", Registry)
    queue, seen, instances = deque(), [], []

    def factory():
        model = ScriptedModel(queue, seen, app.state.settings.public())
        instances.append(model)
        return model

    app = create_app(tmp_path / "service", token="resume-test", model_factory=factory, persist_secrets=False)
    store = app.state.store
    store.set_settings({"model": "original-model", "base_url": "https://example.invalid/v1", "max_steps": 8})
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "main.py").write_bytes(BEFORE.encode())
    workspace_id, session_id = identifier(), identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "workspace"))
    store.execute("INSERT INTO sessions VALUES(?,?,?,?)", (session_id, workspace_id, "注释会话", now()))

    def seed(status="cancelled", skill=ANNOTATION_SKILL, steps=2, messages=None):
        task_id = identifier()
        if messages is None:
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "原始任务上下文"}]
        store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,skill_instructions,"
                      "messages,steps,elapsed,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (task_id, session_id, workspace_id, "注释整个项目", status, skill, load_skill(skill),
                       json.dumps(messages, ensure_ascii=False), steps, 12.5, "旧的停止原因", now(), now()))
        return task_id

    with TestClient(app, headers=AUTH) as client:
        yield SimpleNamespace(app=app, client=client, store=store, root=root, seed=seed, queue=queue,
                              seen=seen, instances=instances, workspace_id=workspace_id, session_id=session_id)


@pytest.mark.parametrize("status", ["cancelled", "interrupted", "failed", "budget_exhausted"])
def test_resume_same_annotation_task_and_preserve_history(service, status):
    s = service
    task_id = s.seed(status)
    original = s.store.one("tasks", task_id)
    old_event = s.store.event(task_id, "task." + status, {"message": "已有执行记录"})
    s.queue.append(action("final", message="继续处理完毕。"))
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 202, response.text
    public = response.json()
    assert public["id"] == task_id and public["session_id"] == s.session_id
    assert public["steps"] == 2 and public["result"] == ""
    assert "messages" not in public and "skill_instructions" not in public
    complete = wait_task(s.client, task_id, "completed")
    assert complete["steps"] == 3 and complete["elapsed"] >= 12.5
    assert s.store.rows("SELECT id FROM tasks") == [{"id": task_id}]
    assert s.store.rows("SELECT id FROM sessions") == [{"id": s.session_id}]
    persisted = s.store.one("tasks", task_id)
    history = json.loads(persisted["messages"])
    assert history[:2] == json.loads(original["messages"])
    assert history[2]["role"] == "user" and "用户点击“继续执行”" in history[2]["content"]
    assert "请先重新 read" in s.seen[0][-1]["content"]
    assert persisted["skill_instructions"] == original["skill_instructions"]
    events = s.store.events(task_id)
    assert events[0] == old_event
    assert [e["kind"] for e in events].count("task.resumed") == 1
    assert next(e for e in events if e["kind"] == "agent.step")["data"]["step"] == 3


def test_new_model_uses_current_settings_after_failure(service):
    s = service
    s.queue.append(RuntimeError("provider unavailable"))
    response = s.client.post("/api/tasks", json={"workspace_id": s.workspace_id,
                             "prompt": "补充注释", "skill": ANNOTATION_SKILL})
    task_id = response.json()["id"]
    failed = wait_task(s.client, task_id, "failed")
    assert failed["steps"] == 1 and s.instances[0].closed
    settings = s.client.put("/api/settings", json={"model": "replacement-model",
        "base_url": "https://replacement.invalid/v1", "api_key": "replacement-key", "max_steps": 12})
    assert settings.status_code == 200
    s.queue.append(action("final", message="切换模型后完成。"))
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    assert wait_task(s.client, task_id, "completed")["steps"] == 2
    assert len(s.instances) == 2 and s.instances[1] is not s.instances[0]
    assert s.instances[1].settings["model"] == "replacement-model"
    assert s.instances[1].settings["max_steps"] == 12
    assert "没有产生可执行结果" in s.seen[1][-1]["content"]


@pytest.mark.parametrize("status", ["queued", "running", "cancelling", "waiting_review", "completed", "rejected"])
def test_resume_refuses_active_finished_and_rejected_tasks(service, status):
    task_id = service.seed(status)
    response = service.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 409
    assert not service.instances and not service.store.events(task_id)
    assert service.store.one("tasks", task_id)["status"] == status


def test_resume_refuses_plain_tasks_missing_tasks_and_unauthenticated_requests(service):
    s = service
    task_id = s.seed("failed", skill=None)
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 409
    assert s.client.post("/api/tasks/missing/resume").status_code == 404
    assert s.client.post(f"/api/tasks/{task_id}/resume", headers={"Authorization": "wrong"}).status_code == 401
    assert not s.instances


@pytest.mark.parametrize("status", ["queued", "running", "cancelling", "waiting_review"])
def test_resume_refuses_another_active_task_in_session(service, status):
    task_id = service.seed()
    service.seed(status)
    response = service.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 409 and "该会话" in response.json()["detail"]
    assert not service.instances


def test_exhausted_budget_requires_increase_and_never_resets_steps(service):
    s = service
    task_id = s.seed("budget_exhausted", steps=8)
    original = s.store.one("tasks", task_id)
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 409
    assert "提高最大步数" in response.json()["detail"] and "8" in response.json()["detail"]
    assert s.store.one("tasks", task_id) == original and not s.instances
    s.store.set_settings({"max_steps": 9})
    s.queue.append(action("read", path="main.py"))
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    exhausted = wait_task(s.client, task_id, "budget_exhausted")
    assert exhausted["steps"] == 9 and "提高最大步数" in exhausted["result"]
    assert len(s.seen) == 1


def test_applied_patches_stay_applied_and_history_can_be_undone_after_resume(service):
    s = service
    task_id = s.seed()
    patch = s.app.state.runtime.patches.propose(s.store.one("tasks", task_id), [
        {"path": "main.py", "base_hash": digest(BEFORE), "content": AFTER}])
    s.app.state.runtime.patches.apply(patch["id"])
    s.queue.append(action("final", message="已确认现有注释。"))
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    complete = wait_task(s.client, task_id, "completed")
    assert len(complete["patches"]) == 1 and complete["patches"][0]["id"] == patch["id"]
    assert complete["patches"][0]["status"] == "applied"
    assert s.root.joinpath("main.py").read_bytes() == AFTER.encode()
    assert patch["id"] in s.seen[0][-1]["content"]
    assert s.client.post(f"/api/patches/{patch['id']}/undo").status_code == 200
    assert s.root.joinpath("main.py").read_bytes() == BEFORE.encode()


@pytest.mark.parametrize("status", ["applying", "undoing", "recovery_required"])
def test_resume_requires_partial_patch_recovery(service, status):
    s = service
    task_id = s.seed("interrupted")
    patch = s.app.state.runtime.patches.propose(s.store.one("tasks", task_id), [
        {"path": "main.py", "base_hash": digest(BEFORE), "content": AFTER}])
    s.store.execute("UPDATE patches SET status=? WHERE id=?", (status, patch["id"]))
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 409 and "先恢复或撤销" in response.json()["detail"]
    assert not s.instances and s.store.one("patches", patch["id"])["status"] == status


def test_unobserved_actions_and_proposed_patches_are_not_replayed(service):
    s = service
    pending = action("propose_patch", changes=[{"path": "main.py", "base_hash": digest(BEFORE), "content": AFTER}])
    history = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "为项目注释"},
               {"role": "assistant", "content": pending, "tool_calls": [{"id": "old-call", "type": "function",
                "function": {"name": "submit_action", "arguments": pending}}]}]
    task_id = s.seed(messages=history)
    patch = s.app.state.runtime.patches.propose(s.store.one("tasks", task_id), [
        {"path": "main.py", "base_hash": digest(BEFORE), "content": AFTER}])
    s.queue.extend([action("read", path="main.py"), action("final", message="重新读取，等待后续补充。")])
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    complete = wait_task(s.client, task_id, "completed")
    assert complete["patches"][0]["status"] == "rejected"
    assert s.root.joinpath("main.py").read_bytes() == BEFORE.encode()
    assert json.loads(s.store.one("tasks", task_id)["messages"])[:3] == history
    continuation = s.seen[0][-1]["content"]
    assert "禁止自动重放旧动作或旧补丁" in continuation and patch["id"] in continuation
    assert "rejected" in continuation
    native = tool_messages(s.seen[0])
    assert not any(item.get("tool_call_id") == "old-call" for item in native)
    assert json.loads(s.seen[1][-1]["content"].removeprefix("工具观察："))["content"] == BEFORE


def test_resumed_task_can_be_stopped_and_deleted_and_double_resume_conflicts(service):
    s = service
    task_id = s.seed()
    s.queue.append("wait")
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    wait_task(s.client, task_id, "running")
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 409
    assert s.client.delete(f"/api/tasks/{task_id}").status_code == 409
    cancelled = s.client.post(f"/api/tasks/{task_id}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert len(s.instances) <= 1
    assert s.client.delete(f"/api/tasks/{task_id}").json() == {"id": task_id, "deleted": True}
    assert not s.store.events(task_id)


def test_cancel_during_background_registry_import_remains_responsive(service, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def delayed_registry():
        entered.set()
        release.wait(3)
        return Registry()

    monkeypatch.setattr("backend.runtime.create_tool_registry", delayed_registry)
    s = service
    task_id = s.seed()
    try:
        assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
        assert entered.wait(2)
        assert s.client.post(f"/api/tasks/{task_id}/cancel").json()["status"] == "cancelled"
        assert s.client.delete(f"/api/tasks/{task_id}").status_code == 200
        assert not s.instances
    finally:
        release.set()


def test_restart_does_not_automatically_execute_stopped_annotation_tasks(service):
    s = service
    ids = {status: s.seed(status) for status in ["running", "interrupted", "cancelled", "failed", "budget_exhausted"]}
    restarted = create_app(s.store.path.parent, token="resume-test",
                           model_factory=lambda: pytest.fail("No model call is allowed on restart"), persist_secrets=False)
    with TestClient(restarted, headers=AUTH) as client:
        assert client.get(f"/api/tasks/{ids['running']}").json()["status"] == "interrupted"
        for status in ["interrupted", "cancelled", "failed", "budget_exhausted"]:
            assert client.get(f"/api/tasks/{ids[status]}").json()["status"] == status
        assert s.root.joinpath("main.py").read_bytes() == BEFORE.encode()


async def test_resume_waits_for_previous_finally_before_reusing_elapsed(service):
    s = service
    task_id = s.seed("failed")
    runtime = s.app.state.runtime
    entered, release = asyncio.Event(), asyncio.Event()

    async def previous_job():
        entered.set()
        await release.wait()
        s.store.update_task(task_id, elapsed=30)

    previous = asyncio.create_task(previous_job())
    runtime.jobs[task_id] = previous
    await entered.wait()
    continuation = asyncio.create_task(runtime.resume(task_id))
    await asyncio.sleep(0)
    assert not continuation.done() and s.store.one("tasks", task_id)["status"] == "failed"
    s.queue.append(action("final", message="继续完成。"))
    release.set()
    resumed = await continuation
    assert resumed["elapsed"] == 30 and resumed["status"] == "queued"
    await runtime.jobs[task_id]
    assert s.store.one("tasks", task_id)["elapsed"] >= 30
    assert s.store.one("tasks", task_id)["steps"] == 3
