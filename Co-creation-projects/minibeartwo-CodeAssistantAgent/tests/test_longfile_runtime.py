"""Long Python annotation converges through durable function-sized model requests."""
from __future__ import annotations

import ast
import asyncio
import inspect
import json
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.model import ModelRequestTimeout
from backend.skills import ANNOTATION_SKILL, validate_annotation_change
from backend.store import identifier
from backend.workspace import digest


AUTH = {"Authorization": "Bearer longfile-runtime-test"}
TERMINAL = {"completed", "failed", "cancelled", "interrupted", "budget_exhausted", "rejected"}


def long_source(function_count=15):
    parts = ['"""The module documentation must stay unchanged."""\n\n']
    for number in range(function_count):
        parts.append(f"def calculate_{number:02d}(value, *, scale=1):\n")
        parts.append(f'    """Implementation marker FUNCTION_{number:02d}."""\n')
        parts.append("    subtotal = value * scale\n")
        parts.extend(f"    # Detailed source context {number:02d}/{line:02d}: " + "padding " * 7 + "\n" for line in range(40))
        parts.append("    return subtotal\n\n")
    text = "".join(parts)
    assert 51_000 < len(text) < 256_000
    return text


def unit_from(messages):
    try:
        value = json.loads(messages[1]["content"])
    except (IndexError, TypeError, ValueError):
        return None
    return value.get("annotation_unit") if value.get("client_mode") == "annotation_unit" else None


def documented_action(unit):
    if unit["kind"] == "header":
        documentation = {
            "purpose": "提供按比例计算数值的示例函数。",
            "input_files": "无。",
            "inputs": "调用方通过内存传入 value 数值和 scale 比例。",
            "output_files": "无。",
            "outputs": "提供各个计算函数的返回值，不写入文件。",
        }
    else:
        parameters = unit.get("parameters", [])
        documentation = {
            "purpose": f"执行 {unit['name']} 的数值计算。",
            "inputs": "；".join(f"{name}：调用方传入的参数" for name in parameters) if parameters else "无。",
            "outputs": "返回按传入比例计算得到的数值。",
        }
    return json.dumps({"action": "annotate_unit", "args": {
        "path": unit["path"], "base_hash": unit["base_hash"],
        "target_id": unit["target_id"], "documentation": documentation,
    }, "summary": "生成当前单元的中文注释草稿"}, ensure_ascii=False)


class Registry:
    def __init__(self):
        self.functions = {}

    def register_function(self, name, description, function):
        self.functions[name] = function

    def execute_tool(self, name, args):
        return self.functions[name](args)


class Controller:
    def __init__(self):
        self.seen, self.models = [], []
        self.handler = None

    def default(self, messages):
        unit = unit_from(messages)
        if unit is not None:
            return documented_action(unit)
        return json.dumps({"action": "final", "args": {"message": "长文件注释已汇总并通过静态校验。"}, "summary": "结束注释"}, ensure_ascii=False)

    def model(self):
        controller = self

        class Model:
            closed = False

            async def generate(self, messages, emit):
                copied = json.loads(json.dumps(messages, ensure_ascii=False))
                controller.seen.append(copied)
                response = controller.handler(copied) if controller.handler else controller.default(copied)
                return await response if inspect.isawaitable(response) else response

            def close(self):
                self.closed = True

        result = Model()
        self.models.append(result)
        return result


def wait_terminal(s, task_id, expected="completed", timeout=12):
    deadline = time.monotonic() + timeout
    task = None
    while time.monotonic() < deadline:
        response = s.client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in TERMINAL:
            assert task["status"] == expected, {key: task[key] for key in ("id", "status", "steps", "result")}
            return task
        time.sleep(.01)
    pytest.fail(f"Expected {expected}, got {task['status'] if task else None}")


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.runtime.create_tool_registry", Registry)
    monkeypatch.setattr("backend.runtime.REQUEST_RETRY_DELAYS", (0,))
    controller = Controller()
    data = tmp_path / "service"
    root = tmp_path / "workspace"
    root.mkdir()
    before = long_source()
    source = root / "large.py"
    source.write_bytes(before.encode())
    s = SimpleNamespace(root=root, source=source, before=before, controller=controller, data=data)

    def start():
        s.app = create_app(data, token="longfile-runtime-test", model_factory=controller.model, persist_secrets=False)
        s.store = s.app.state.store
        s.store.set_settings({"model": "local-fake-model", "base_url": "https://example.invalid/v1", "max_steps": 100})
        s.client = TestClient(s.app, headers=AUTH)
        s.client.__enter__()

    def restart():
        s.client.__exit__(None, None, None)
        start()

    start()
    s.workspace_id = identifier()
    s.store.execute("INSERT INTO workspaces VALUES(?,?,?)", (s.workspace_id, str(root), "workspace"))

    def create():
        response = s.client.post("/api/tasks", json={"workspace_id": s.workspace_id,
            "prompt": "为完整项目添加中文文件头和逐函数注释，仅静态检查。", "skill": ANNOTATION_SKILL})
        assert response.status_code == 202, response.text
        return response.json()["id"]

    s.create, s.restart = create, restart
    try:
        yield s
    finally:
        s.client.__exit__(None, None, None)


def test_large_python_converges_with_one_bounded_request_per_unit_and_one_atomic_patch(service):
    s = service
    source_seen_while_generating = []

    def respond(messages):
        if unit_from(messages):
            source_seen_while_generating.append(s.source.read_bytes().decode())
        return s.controller.default(messages)

    s.controller.handler = respond
    task_id = s.create()
    task = wait_terminal(s, task_id)
    prompts = [messages for messages in s.controller.seen if unit_from(messages)]
    units = [unit_from(messages) for messages in prompts]
    assert len(units) == 16 and sum(unit["kind"] == "header" for unit in units) == 1
    assert len({unit["target_id"] for unit in units}) == 16
    assert [unit["progress"]["done"] for unit in units] == list(range(16))
    assert all(len(messages) == 2 for messages in prompts)
    assert all(sum(len(item["content"]) for item in messages) < 30_000 for messages in prompts)
    assert all(original == s.before for original in source_seen_while_generating), "Drafts must never partially write the source."
    for unit in units:
        if unit["kind"] == "function":
            assert unit["name"].split(".")[-1] in unit["source"]
            assert unit["source"].count("Implementation marker FUNCTION_") == 1
    after = s.source.read_bytes().decode()
    assert after != s.before
    assert ast.dump(ast.parse(after), include_attributes=False) == ast.dump(ast.parse(s.before), include_attributes=False)
    assert validate_annotation_change("large.py", s.before, after)["functions"] == 15
    assert len(task["patches"]) == 1 and task["patches"][0]["status"] == "applied"
    assert task["steps"] == 17
    assert not any(event["kind"] == "agent.loop_warning" for event in s.store.events(task_id))
    assert s.client.post(f"/api/patches/{task['patches'][0]['id']}/undo").status_code == 200
    assert s.source.read_bytes().decode() == s.before


def test_budget_then_restart_and_resume_reuses_header_draft_and_cumulative_steps(service):
    s = service
    s.store.set_settings({"max_steps": 1})
    task_id = s.create()
    paused = wait_terminal(s, task_id, "budget_exhausted")
    assert paused["steps"] == 1 and not paused["patches"]
    first = unit_from(s.controller.seen[0])
    assert first["kind"] == "header" and s.source.read_bytes().decode() == s.before
    s.restart()
    before_resume = len(s.controller.seen)
    response = s.client.post(f"/api/tasks/{task_id}/resume")
    assert response.status_code == 202, response.text
    task = wait_terminal(s, task_id)
    resumed = unit_from(s.controller.seen[before_resume])
    assert resumed["kind"] == "function" and resumed["target_id"] != first["target_id"]
    assert resumed["progress"]["done"] == 1
    assert sum(unit_from(messages).get("kind") == "header" for messages in s.controller.seen if unit_from(messages)) == 1
    assert task["steps"] == 17 and len(task["patches"]) == 1


def test_manual_cancel_during_a_unit_resumes_that_unit_without_losing_completed_drafts(service):
    s = service
    entered = threading.Event()
    waiting_unit = {}

    async def respond(messages):
        unit = unit_from(messages)
        if unit and unit["progress"]["done"] == 2:
            waiting_unit.update(unit)
            entered.set()
            await asyncio.Event().wait()
        return s.controller.default(messages)

    s.controller.handler = respond
    task_id = s.create()
    assert entered.wait(8), "The third deterministic unit was never requested."
    stopped = s.client.post(f"/api/tasks/{task_id}/cancel").json()
    assert stopped["status"] == "cancelled" and not stopped.get("patches", [])
    assert s.source.read_bytes().decode() == s.before
    assert s.controller.models[0].closed
    s.controller.handler = None
    s.restart()
    start_index = len(s.controller.seen)
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    done = wait_terminal(s, task_id)
    resumed = unit_from(s.controller.seen[start_index])
    assert resumed["target_id"] == waiting_unit["target_id"] and resumed["progress"]["done"] == 2
    assert done["steps"] == stopped["steps"] + 15
    assert len(done["patches"]) == 1


def test_external_source_change_discards_stale_drafts_and_preserves_the_users_change(service):
    s = service
    s.store.set_settings({"max_steps": 1})
    task_id = s.create()
    wait_terminal(s, task_id, "budget_exhausted")
    old_unit = unit_from(s.controller.seen[0])
    changed = s.before + "\nUSER_ADDED_VALUE = 7\n"
    s.source.write_bytes(changed.encode())
    s.restart()
    start_index = len(s.controller.seen)
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    task = wait_terminal(s, task_id)
    rebuilt = unit_from(s.controller.seen[start_index])
    assert rebuilt["kind"] == "header" and rebuilt["progress"]["done"] == 0
    assert rebuilt["base_hash"] != old_unit["base_hash"] and rebuilt["target_id"] != old_unit["target_id"]
    after = s.source.read_bytes().decode()
    assert "USER_ADDED_VALUE = 7" in after
    assert ast.dump(ast.parse(after), include_attributes=False) == ast.dump(ast.parse(changed), include_attributes=False)
    assert len(task["patches"]) == 1


@pytest.mark.parametrize("corruption", ["target", "fields"])
def test_invalid_unit_output_never_writes_source_or_applies_a_partial_file(service, corruption):
    s = service
    s.store.set_settings({"max_steps": 1})

    def respond(messages):
        unit = unit_from(messages)
        assert unit is not None
        response = json.loads(documented_action(unit))
        if corruption == "target":
            response["args"]["target_id"] = "invented-target"
        else:
            response["args"]["documentation"].pop("outputs")
        return json.dumps(response, ensure_ascii=False)

    s.controller.handler = respond
    task_id = s.create()
    task = wait_terminal(s, task_id, "budget_exhausted")
    assert not task["patches"] and s.source.read_bytes().decode() == s.before
    assert any(event["kind"] == "tool.error" for event in s.store.events(task_id))
    s.controller.handler = None
    s.store.set_settings({"max_steps": 100})
    start_index = len(s.controller.seen)
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    done = wait_terminal(s, task_id)
    assert unit_from(s.controller.seen[start_index])["kind"] == "header"
    assert len(done["patches"]) == 1


def test_timeout_retries_same_unit_without_consuming_more_steps_or_losing_drafts(service):
    s = service
    attempts = 0

    def respond(messages):
        nonlocal attempts
        unit = unit_from(messages)
        if unit and unit["kind"] == "header" and attempts < 13:
            attempts += 1
            raise ModelRequestTimeout("temporary provider timeout")
        return s.controller.default(messages)

    s.controller.handler = respond
    task_id = s.create()
    task = wait_terminal(s, task_id)
    retried = [unit_from(messages) for messages in s.controller.seen[:14]]
    assert len({unit["target_id"] for unit in retried}) == 1
    assert task["steps"] == 17 and len(s.controller.seen) == 30
    assert len(task["patches"]) == 1
    events = s.store.events(task_id)
    assert sum(event["kind"] == "model.retry" for event in events) == 13
    assert not any(event["kind"] in {"agent.loop_warning", "task.interrupted"} for event in events)


def test_model_cannot_reenter_page_read_loop_while_the_client_is_scheduling_annotation_units(service):
    s = service

    def repeat_read(messages):
        assert unit_from(messages) is not None
        return json.dumps({"action": "read", "args": {"path": "large.py", "start_line": 1},
                           "summary": "模型试图再次读取第一页"}, ensure_ascii=False)

    s.controller.handler = repeat_read
    task_id = s.create()
    paused = wait_terminal(s, task_id, "interrupted")
    assert paused["steps"] == len(s.controller.seen) == 3
    assert not paused["patches"] and s.source.read_bytes().decode() == s.before
    events = s.store.events(task_id)
    assert sum(event["kind"] == "tool.error" for event in events) == 3
    history = json.loads(s.store.one("tasks", task_id)["messages"])
    actual_observations = [json.loads(item["content"].removeprefix("工具观察：")) for item in history
                           if item["content"].startswith("工具观察：")]
    assert not any(item.get("content") == s.before for item in actual_observations)
    assert all(item.get("status") == "error" for item in actual_observations)
    s.controller.handler = None
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    completed = wait_terminal(s, task_id)
    assert completed["steps"] == 20 and len(completed["patches"]) == 1


def test_provider_balance_failure_is_not_retried_as_a_unit_format_or_validation_error(service):
    s = service

    def unavailable(messages):
        assert unit_from(messages) is not None
        raise ValueError("402 insufficient balance")

    s.controller.handler = unavailable
    task_id = s.create()
    failed = wait_terminal(s, task_id, "failed")
    assert failed["steps"] == len(s.controller.seen) == 1
    assert "402 insufficient balance" in failed["result"]
    assert not failed["patches"] and s.source.read_bytes().decode() == s.before
    kinds = [event["kind"] for event in s.store.events(task_id)]
    assert "task.failed" in kinds
    assert not set(kinds) & {"tool.error", "model.retry", "annotation.staged"}
    s.controller.handler = None
    first_resume = len(s.controller.seen)
    assert s.client.post(f"/api/tasks/{task_id}/resume").status_code == 202
    completed = wait_terminal(s, task_id)
    unit = unit_from(s.controller.seen[first_resume])
    assert unit["kind"] == "header" and unit["progress"]["done"] == 0
    assert completed["steps"] == 18 and len(completed["patches"]) == 1


def test_invalid_full_candidate_preserves_source_and_drafts_and_continues_other_files(service):
    s = service
    # Replacing a metadata line that also carries a licence is intentionally
    # unsupported; this must not prevent the rest of the project from advancing.
    s.before = '# 代码用途：Copyright original owner\n' + s.before
    s.source.write_bytes(s.before.encode())
    small = s.root / 'small.py'
    small.write_bytes(b'value = 1\n')
    annotated = ('# 代码用途：定义示例值。\n# 输入文件：无。\n# 输入说明：无。\n'
                 '# 输出文件：无。\n# 输出说明：提供 value。\nvalue = 1\n')
    ordinary = []

    def respond(messages):
        unit = unit_from(messages)
        if unit:
            return documented_action(unit)
        ordinary.append(True)
        if len(ordinary) == 1:
            action = {'action': 'read', 'args': {'path': 'small.py'}}
        elif len(ordinary) == 2:
            action = {'action': 'propose_patch', 'args': {'changes': [
                {'path': 'small.py', 'base_hash': digest('value = 1\n'), 'content': annotated}]}}
        else:
            action = {'action': 'final', 'args': {'message': '小文件已完成，大文件受阻且未写入。'}}
        return json.dumps(action, ensure_ascii=False)

    s.controller.handler = respond
    task_id = s.create()
    task = wait_terminal(s, task_id)
    assert s.source.read_bytes().decode() == s.before
    assert small.read_bytes().decode() == annotated
    assert len(task['patches']) == 1 and task['patches'][0]['changes'][0]['path'] == 'small.py'
    assert '受阻 1 个文件' in task['result']
    saved = json.loads(s.store.rows('SELECT state FROM annotation_drafts WHERE task_id=?', (task_id,))[0]['state'])
    assert len(saved['documents']) == 16
    assert any(event['kind'] == 'annotation.blocked' for event in s.store.events(task_id))
