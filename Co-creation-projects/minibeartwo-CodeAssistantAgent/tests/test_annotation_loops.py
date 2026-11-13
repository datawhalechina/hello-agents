"""Real tool failures, repeated actions and long-file annotation convergence."""
from __future__ import annotations

import ast
import asyncio
import json
import time
from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.model import ModelRequestTimeout
from backend.patches import Patches
from backend.runtime import SYSTEM, context_messages
from backend.skills import ANNOTATION_SKILL, load_skill
from backend.store import identifier, now
from backend.workspace import digest


AUTH = {"Authorization": "Bearer annotation-loop-test"}
BEFORE = "value = 1\n"
HEADER = ("# 代码用途：定义供调用方使用的示例数值。\n# 输入文件：无。\n"
          "# 输入说明：无外部输入。\n# 输出文件：无。\n# 输出说明：提供 value 数值。\n")
AFTER = HEADER + BEFORE
TERMINAL = {"completed", "failed", "cancelled", "interrupted", "budget_exhausted", "rejected"}


def action(name, **args):
    return json.dumps({"action": name, "args": args, "summary": name}, ensure_ascii=False)


def observation(messages):
    text = messages[-1]["content"]
    assert text.startswith("工具观察："), text[:300]
    return json.loads(text.removeprefix("工具观察："))


class SwallowingRegistry:
    """Match the framework behavior that previously hid local tool exceptions."""

    def __init__(self):
        self.functions, self.executed = {}, []

    def register_function(self, name, description, function):
        self.functions[name] = function

    def execute_tool(self, name, args):
        self.executed.append(name)
        try:
            return self.functions[name](args)
        except Exception as exc:
            return "framework swallowed tool exception: " + str(exc)


class ScriptedModel:
    def __init__(self, script, seen):
        self.script, self.seen = script, seen

    async def generate(self, messages, emit):
        self.seen.append(messages)
        response = self.script.popleft()
        if isinstance(response, Exception):
            raise response
        if response == "wait":
            await asyncio.Event().wait()
        return response(messages) if callable(response) else response

    def close(self):
        pass


def wait_terminal(service, task_id, expected="completed", timeout=8):
    deadline = time.monotonic() + timeout
    task = None
    while time.monotonic() < deadline:
        response = service.client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in TERMINAL:
            assert task["status"] == expected, task
            return task
        time.sleep(.01)
    pytest.fail(f"Expected {expected}, got {task}")


@pytest.fixture
def service(tmp_path, monkeypatch):
    registries = []

    def registry_factory():
        registry = SwallowingRegistry()
        registries.append(registry)
        return registry

    monkeypatch.setattr("backend.runtime.create_tool_registry", registry_factory)
    monkeypatch.setattr("backend.runtime.REQUEST_RETRY_DELAYS", (0,))
    queue, seen = deque(), []
    app = create_app(tmp_path / "service", token="annotation-loop-test",
                     model_factory=lambda: ScriptedModel(queue, seen), persist_secrets=False)
    store = app.state.store
    store.set_settings({"model": "fake-model", "base_url": "https://example.invalid/v1", "max_steps": 100})
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "a.py").write_bytes(BEFORE.encode())
    workspace_id = identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "workspace"))
    with TestClient(app, headers=AUTH) as client:
        def create(skill=ANNOTATION_SKILL):
            response = client.post("/api/tasks", json={"workspace_id": workspace_id,
                                  "prompt": "为整个项目添加中文注释", "skill": skill})
            assert response.status_code == 202, response.text
            return response.json()["id"]

        yield SimpleNamespace(app=app, client=client, store=store, root=root, queue=queue,
                              seen=seen, registries=registries, create=create, workspace_id=workspace_id)


@pytest.mark.parametrize("args", [{"path": "missing.py"}, {}, {"path": "../outside.py"}])
def test_annotation_tool_exceptions_are_real_structured_errors_even_when_registry_swallows(service, args):
    s = service
    s.queue.extend([action("read", **args), action("final", message="读取失败，未完成注释。")])
    task_id = s.create()
    wait_terminal(s, task_id)
    actual = observation(s.seen[1])
    assert actual["status"] == "error" and actual["action"] == "read"
    assert actual["error"] and actual["message"] and actual["recovery"]
    assert "framework swallowed" not in json.dumps(actual)
    assert s.registries[0].executed == [], "Annotation tools must bypass exception-swallowing execute_tool."
    assert any(item["kind"] == "tool.error" for item in s.store.events(task_id))
    assert (s.root / "a.py").read_bytes() == BEFORE.encode()


def test_alternating_repeated_reads_and_inventory_pause_and_can_resume_without_losing_patch(service):
    s = service
    s.queue.extend([action("read", path="a.py"), action("propose_patch", changes=[{
        "path": "a.py", "base_hash": digest(BEFORE), "content": AFTER}])])
    s.queue.extend([item for _ in range(15) for item in
                    [action("read", path="a.py"), action("inventory", offset=0)]])
    s.queue.append(action("final", message="不应在停滞后继续消耗所有步数。"))
    task_id = s.create()
    paused = wait_terminal(s, task_id, "interrupted")
    assert 6 <= paused["steps"] < 30
    assert len(paused["patches"]) == 1 and paused["patches"][0]["status"] == "applied"
    assert (s.root / "a.py").read_bytes() == AFTER.encode()
    events = s.store.events(task_id)
    kinds = [event["kind"] for event in events]
    assert kinds.index("agent.loop_warning") < kinds.index("task.interrupted")
    old_messages = json.loads(s.store.one("tasks", task_id)["messages"])
    old_steps, patch_id, last_event = paused["steps"], paused["patches"][0]["id"], events[-1]["id"]
    s.queue.clear()
    s.queue.append(action("final", message="已保留注释，结束继续执行。"))
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 202, response.text
    complete = wait_terminal(s, task_id)
    assert complete["id"] == task_id and complete["steps"] == old_steps + 1
    assert complete["patches"][0]["id"] == patch_id
    assert json.loads(s.store.one("tasks", task_id)["messages"])[:len(old_messages)] == old_messages
    resumed_events = s.store.events(task_id, after=last_event)
    assert any(event["kind"] == "task.resumed" for event in resumed_events)
    assert not any(event["kind"] == "agent.loop_warning" for event in resumed_events)


def test_repeated_patch_validation_errors_trigger_guard_without_writing_files(service):
    s = service
    s.queue.append(action("read", path="a.py"))
    bad = action("propose_patch", changes=[{"path": "a.py", "base_hash": digest(BEFORE),
        "edits": [{"old": "this text does not exist", "new": "# 注释\nthis text does not exist"}]}])
    s.queue.extend([bad] * 20)
    task_id = s.create()
    paused = wait_terminal(s, task_id, "interrupted")
    assert paused["steps"] < 20 and not paused["patches"]
    assert (s.root / "a.py").read_bytes() == BEFORE.encode()
    events = s.store.events(task_id)
    assert sum(event["kind"] == "tool.error" for event in events) >= 3
    assert any(event["kind"] == "agent.loop_warning" for event in events)
    observations = [json.loads(item["content"].removeprefix("工具观察："))
                    for item in json.loads(s.store.one("tasks", task_id)["messages"])
                    if item["content"].startswith("工具观察：")]
    failures = [item for item in observations if item.get("status") == "error"]
    assert failures and all(item["action"] == "propose_patch" and item["recovery"] for item in failures)


def test_transport_timeout_retries_do_not_count_as_repeated_workspace_actions(service):
    s = service
    s.queue.extend([ModelRequestTimeout("temporary provider timeout")] * 14)
    s.queue.extend([action("read", path="a.py"), action("final", message="连接恢复，尚未完成注释。")])
    task_id = s.create()
    complete = wait_terminal(s, task_id)
    assert complete["steps"] == 2
    events = s.store.events(task_id)
    assert sum(event["kind"] == "model.retry" for event in events) == 14
    assert not any(event["kind"] in {"agent.loop_warning", "task.interrupted"} for event in events)


def test_distinct_file_reads_are_progress_even_when_contents_have_identical_hashes(service):
    s = service
    for number in range(18):
        relative = f"item_{number:02d}.py"
        (s.root / relative).write_bytes(BEFORE.encode())
        s.queue.append(action("read", path=relative))
    s.queue.append(action("final", message="已读取 18 个不同文件，尚未写入注释。"))
    task_id = s.create()
    complete = wait_terminal(s, task_id)
    assert complete["steps"] == 19
    assert not any(event["kind"] == "agent.loop_warning" for event in s.store.events(task_id))


def test_large_python_file_is_annotated_in_units_without_whole_file_context(service):
    s = service
    before = "".join(f"sample_{number:04d} = {number}\n" for number in range(2800))
    before += "\ndef get_value(value):\n    return value\n"
    assert 51_000 < len(before) < 256_000
    (s.root / "a.py").write_bytes(before.encode())
    function = ("# 函数用途：返回调用方传入的值。\n# 输入说明：value：需要返回的值。\n"
                "# 输出说明：返回 value 本身。\n")
    units = []

    def next_action(messages):
        request = json.loads(messages[1]['content'])
        if request.get('client_mode') != 'annotation_unit':
            return action('final', message='大文件注释已通过静态检查并应用。')
        unit = request['annotation_unit']
        units.append(unit)
        docs = {'purpose': '提供示例数值与原值返回函数。', 'inputs': 'value：调用方传入的值。', 'outputs': '返回传入的 value。'}
        if unit['kind'] == 'header':
            docs.update(input_files='无。', output_files='无。')
        return action('annotate_unit', path=unit['path'], base_hash=unit['base_hash'],
                      target_id=unit['target_id'], documentation=docs)

    s.queue.extend([next_action] * 8)
    task_id = s.create()
    complete = wait_terminal(s, task_id)
    assert len(units) == 2 and {unit['kind'] for unit in units} == {'header', 'function'}
    assert all(len(json.dumps(unit, ensure_ascii=False)) <= 22_000 for unit in units)
    assert all(unit['base_hash'] == digest(before) for unit in units)
    assert len(complete["patches"]) == 1 and complete["patches"][0]["status"] == "applied"
    actual = (s.root / "a.py").read_bytes().decode()
    assert actual != before
    assert ast.dump(ast.parse(actual), include_attributes=False) == ast.dump(ast.parse(before), include_attributes=False)
    assert not any(event["kind"] == "agent.loop_warning" for event in s.store.events(task_id))


def test_long_file_edit_limit_is_preserved_for_non_annotation_tasks(service):
    s = service
    before = "".join(f"value_{number} = {number}\n" for number in range(3000))
    assert len(before) > 51_000
    (s.root / "a.py").write_bytes(before.encode())
    task = {"id": "not-saved", "workspace_id": s.workspace_id, "skill": None}
    with pytest.raises(ValueError, match="24000"):
        Patches(s.store).propose(task, [{"path": "a.py", "base_hash": digest(before),
            "edits": [{"old": "value_0 = 0\n", "new": "# 说明\nvalue_0 = 0\n"}]}])
    assert not s.store.rows("SELECT id FROM patches")
    assert (s.root / "a.py").read_bytes() == before.encode()


def test_verified_python_re_reads_are_lightweight_and_next_files_prioritize_unfinished_sources(service):
    s = service
    (s.root / "a.py").write_bytes(AFTER.encode())
    (s.root / "b.py").write_bytes(BEFORE.encode())
    s.queue.extend([action("inventory", offset=0), action("read", path="a.py"),
                    action("read", path="a.py"), action("final", message="a.py 已校验，b.py 尚未处理。")])
    task_id = s.create()
    wait_terminal(s, task_id)
    first_read = observation(s.seen[2])
    assert first_read['content'] == AFTER and first_read['fully_read'] is True
    for prompt in s.seen[3:4]:
        actual = observation(prompt)
        assert actual["status"] == "verified" and actual["already_complete"] is True
        assert actual["content"] == "" and actual["hash"] == digest(AFTER)
        summary = json.loads(prompt[1]["content"])["annotation_progress"]
        assert any(item["path"] == "b.py" for item in summary["next_files"])
        assert not any(item["path"] == "a.py" for item in summary["next_files"])


@pytest.mark.parametrize('attempt', ['read', 'propose_patch'])
def test_long_annotation_unit_cannot_reenter_whole_file_read_or_patch_loop(service, attempt):
    s = service
    before = ''.join(f'value_{number} = {number}\n' for number in range(3000))
    (s.root / 'a.py').write_bytes(before.encode())
    s.queue.extend([action(attempt, path='a.py')] * 3)
    task_id = s.create()
    paused = wait_terminal(s, task_id, 'interrupted')
    assert paused['steps'] == 3 and 'annotate_unit' in paused['result']
    assert all(json.loads(prompt[1]['content'])['client_mode'] == 'annotation_unit' for prompt in s.seen)
    assert not paused['patches'] and (s.root / 'a.py').read_bytes() == before.encode()


def test_new_search_matches_are_progress_but_different_queries_with_same_results_are_not(service):
    s = service
    (s.root / 'search.py').write_bytes(''.join(f'# marker_{number:02d}\n' for number in range(16)).encode())
    s.queue.extend(action('search', query=f'marker_{number:02d}') for number in range(16))
    s.queue.append(action('final', message='已检查不同的真实匹配，尚未写入。'))
    task_id = s.create()
    complete = wait_terminal(s, task_id)
    assert complete['steps'] == 17
    assert not any(e['kind'] == 'agent.loop_warning' for e in s.store.events(task_id))
    s.queue.extend(action('search', query=query) for _ in range(8) for query in ('value', '= 1', 'value ='))
    second = s.create()
    paused = wait_terminal(s, second, 'interrupted')
    assert paused['steps'] < 20 and not paused['patches']


def test_annotation_progress_remains_pinned_after_observation_history_is_trimmed():
    progress = {"counts": {"total": 3, "applied": 1, "verified": 1, "pending": 1},
                "next_files": [{"path": "pending.py", "status": "pending", "next_start_line": 1}],
                "recent_completed": [{"path": "applied.py", "status": "applied", "hash": "actual-hash"}],
                "blocked": []}
    task = {"prompt": "为完整项目注释", "selected_file": None, "test_argv": "[]",
            "skill": ANNOTATION_SKILL, "skill_instructions": load_skill(ANNOTATION_SKILL),
            "workspace_root": "workspace", "annotation_progress": progress}
    history = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "old completed-file ledger"}]
    history.extend({"role": "user", "content": "unrelated observation " * 2000} for _ in range(30))
    messages = context_messages(history, task)
    assert json.loads(messages[1]["content"])["annotation_progress"] == progress
    assert not any(item["content"] == "old completed-file ledger" for item in messages)
    assert sum(len(item["content"]) for item in messages) < 56_000


@pytest.mark.parametrize("externally_changed", [False, True])
def test_legacy_task_resume_recovers_applied_file_progress_from_actual_patch_and_current_hash(service, externally_changed):
    s = service
    (s.root / "b.py").write_bytes(BEFORE.encode())
    task_id, session_id = identifier(), identifier()
    s.store.execute("INSERT INTO sessions VALUES(?,?,?,?)", (session_id, s.workspace_id, "旧注释任务", now()))
    s.store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,skill_instructions,"
                    "messages,steps,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (task_id, session_id, s.workspace_id, "为完整项目注释", "interrupted", ANNOTATION_SKILL,
                     load_skill(ANNOTATION_SKILL), json.dumps([{"role": "system", "content": SYSTEM}]),
                     7, now(), now()))
    patch = s.app.state.runtime.patches.propose(s.store.one("tasks", task_id), [
        {"path": "a.py", "base_hash": digest(BEFORE), "content": AFTER}])
    s.app.state.runtime.patches.apply(patch["id"])
    if externally_changed:
        (s.root / "a.py").write_bytes((AFTER + "def new_function():\n    return 2\n").encode())
    s.queue.extend([action("read", path="b.py"), action("final", message="保留原注释，b.py 待补充。")])
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 202, response.text
    complete = wait_terminal(s, task_id)
    assert complete["steps"] == 9 and complete["patches"][0]["id"] == patch["id"]
    summary = json.loads(s.seen[0][1]["content"])["annotation_progress"]
    if externally_changed:
        assert any(item["path"] == "a.py" for item in summary["next_files"])
        assert not any(item["path"] == "a.py" for item in summary["recent_completed"])
        assert (s.root / "a.py").read_bytes() == (AFTER + "def new_function():\n    return 2\n").encode()
    else:
        completed = next(item for item in summary["recent_completed"] if item["path"] == "a.py")
        assert completed["status"] in {"applied", "verified"} and completed["hash"] == digest(AFTER)
        assert not any(item["path"] == "a.py" for item in summary["next_files"])
        assert (s.root / "a.py").read_bytes() == AFTER.encode()
