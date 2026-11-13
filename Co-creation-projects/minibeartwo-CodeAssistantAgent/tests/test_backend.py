"""Integration checks for the boundaries that can affect real project files."""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.commands import run_command
from backend.runtime import Runtime, context_messages
from backend.settings import Settings
from backend.store import Store, identifier, now
from backend.workspace import Conflict, Workspace, digest


def action(name, **args):
    return json.dumps({"action": name, "args": args, "summary": name}, ensure_ascii=False)


class ScriptedModel:
    def __init__(self, script):
        self.script = script

    async def generate(self, messages, emit):
        item = self.script.popleft()
        if item == "wait":
            await asyncio.sleep(30)
        return item(messages) if callable(item) else item

    def close(self):
        pass


def configured_app(tmp_path, script):
    queue = deque(script)
    app = create_app(tmp_path / "data", token="test-token", model_factory=lambda: ScriptedModel(queue), persist_secrets=False)
    return app, queue


def open_workspace(client, tmp_path):
    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    response = client.post("/api/workspaces", json={"path": str(root)})
    assert response.status_code == 200, response.text
    return root, response.json()["id"]


def wait_task(client, task_id, status, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = client.get(f"/api/tasks/{task_id}").json()
        if task["status"] == status:
            return task
        if task["status"] in {"failed", "budget_exhausted"} and status != task["status"]:
            pytest.fail(str(task))
        time.sleep(0.025)
    pytest.fail(f"Expected {status}, got {task}")


@pytest.fixture
def headers():
    return {"Authorization": "Bearer test-token"}


def test_authenticated_api_file_versions_and_private_files(tmp_path, headers):
    app, _ = configured_app(tmp_path, [])
    with TestClient(app, headers=headers) as client:
        assert client.get("/health", headers={"Authorization": "wrong"}).status_code == 200
        assert client.get("/api/settings", headers={"Authorization": "wrong"}).status_code == 401
        root, workspace_id = open_workspace(client, tmp_path)
        (root / "app.py").write_text("value = 1\n", encoding="utf-8")
        (root / ".env").write_text("SECRET=not-for-model", encoding="utf-8")
        (root / "cert.key").write_text("private", encoding="utf-8")
        base = f"/api/workspaces/{workspace_id}"
        file = client.get(base + "/file", params={"path": "app.py"}).json()
        for path in ["../outside.txt", ".env", "cert.key", ".git/config", "node_modules/pkg.js"]:
            assert client.get(base + "/file", params={"path": path}).status_code == 400
        (root / "app.py").write_text("value = 2\n", encoding="utf-8")
        response = client.put(base + "/file", json={"path": "app.py", "content": "value = 3\n", "base_hash": file["hash"]})
        assert response.status_code == 409
        assert (root / "app.py").read_text() == "value = 2\n"
        current = client.get(base + "/file", params={"path": "app.py"}).json()
        saved = client.put(base + "/file", json={"path": "app.py", "content": "value = 3\n", "base_hash": current["hash"]})
        assert saved.status_code == 200
        assert saved.json()["hash"] == digest("value = 3\n")
        assert client.get(base + "/search", params={"query": "not-for-model"}).json() == []
        result = client.get(base + "/search", params={"query": "VALUE"}).json()
        assert result[0]["path"] == "app.py" and result[0]["line"] == 1


def test_patch_review_runs_real_tests_replays_events_and_undoes(tmp_path, headers):
    before = "def add(a, b):\n    return a - b\n"
    after = "def add(a, b):\n    return a + b\n"
    script = [action("read", path="calculator.py"), action("propose_patch", changes=[{
        "path": "calculator.py", "base_hash": digest(before), "content": after,
    }]), action("test"), action("final", message="已修复 add；真实测试通过。")]
    app, _ = configured_app(tmp_path, script)
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        (root / "calculator.py").write_text(before, encoding="utf-8", newline="")
        (root / "test_calculator.py").write_text("from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8", newline="")
        created = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "修复加法", "test_argv": ["python", "-m", "pytest", "-q"]})
        assert created.status_code == 202
        task_id = created.json()["id"]
        paused = wait_task(client, task_id, "waiting_review")
        patch_id = paused["patches"][0]["id"]
        assert (root / "calculator.py").read_text() == before
        assert "+    return a + b" in paused["patches"][0]["changes"][0]["diff"]
        assert client.post(f"/api/patches/{patch_id}/review", json={"accept": True}).status_code == 200
        complete = wait_task(client, task_id, "completed")
        assert complete["steps"] == 4
        assert (root / "calculator.py").read_text() == after
        events = app.state.store.events(task_id)
        command = next(event for event in events if event["kind"] == "command.completed")
        assert command["data"]["exit_code"] == 0
        assert any("passed" in event["data"].get("text", "") for event in events)
        replay = client.get(f"/api/tasks/{task_id}/events", headers={"Last-Event-ID": str(command["id"])}).text
        replay_ids = [int(line[4:]) for line in replay.splitlines() if line.startswith("id: ")]
        assert replay_ids and min(replay_ids) > command["id"]
        assert client.post(f"/api/patches/{patch_id}/undo").status_code == 200
        assert (root / "calculator.py").read_text() == before
        history = client.get(f"/api/sessions/{complete['session_id']}/tasks").json()
        assert history[0]["status"] == "completed"
        assert "messages" not in history[0]


@pytest.mark.parametrize("alias", ["", ".", "./", ".\\"])
def test_root_directory_listing_accepts_root_aliases_without_opening_file_boundaries(tmp_path, headers, alias):
    app, _ = configured_app(tmp_path, [])
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        (root / 'main.py').write_text('value = 1\n', encoding='utf-8')
        (root / '.env').write_text('SECRET=hidden', encoding='utf-8')
        (root / '.git').mkdir()
        base = f'/api/workspaces/{workspace_id}'
        listed = client.get(base + '/tree', params={'path': alias})
        assert listed.status_code == 200, listed.text
        assert [entry['path'] for entry in listed.json()] == ['main.py']
        assert client.get(base + '/file', params={'path': '.'}).status_code == 400
        for outside in ['..', '../outside', str(root.parent), '.git']:
            assert client.get(base + '/tree', params={'path': outside}).status_code == 400


def test_review_conflict_preserves_external_edit_and_regenerates(tmp_path, headers):
    before, external, final = "old\n", "external edit\n", "external edit\nfixed\n"
    script = [action("propose_patch", changes=[{"path": "file.txt", "base_hash": digest(before), "content": "obsolete\n"}]),
              action("read", path="file.txt"),
              action("propose_patch", changes=[{"path": "file.txt", "base_hash": digest(external), "content": final}]),
              action("final", message="保留外部修改后完成。")]
    app, _ = configured_app(tmp_path, script)
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        (root / "file.txt").write_text(before, encoding="utf-8", newline="")
        task_id = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "修复"}).json()["id"]
        task = wait_task(client, task_id, "waiting_review")
        first = task["patches"][0]["id"]
        (root / "file.txt").write_text(external, encoding="utf-8", newline="")
        assert client.post(f"/api/patches/{first}/review", json={"accept": True}).status_code == 200
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            task = client.get(f"/api/tasks/{task_id}").json()
            if task["status"] == "waiting_review" and len(task["patches"]) == 2:
                break
            time.sleep(0.025)
        assert len(task["patches"]) == 2
        assert task["patches"][0]["status"] == "conflicted"
        assert (root / "file.txt").read_text() == external
        second = task["patches"][1]["id"]
        client.post(f"/api/patches/{second}/review", json={"accept": True})
        wait_task(client, task_id, "completed")
        assert (root / "file.txt").read_text() == final
        (root / "file.txt").write_text("new manual edit\n", encoding="utf-8")
        assert client.post(f"/api/patches/{second}/undo").status_code == 409
        assert (root / "file.txt").read_text() == "new manual edit\n"


def test_all_files_checked_before_writing_and_restart_recovery(tmp_path):
    store = Store(tmp_path / "state.sqlite3")
    root = tmp_path / "workspace"
    root.mkdir()
    workspace_id, task_id = identifier(), identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "workspace"))
    store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (task_id, identifier(), workspace_id, "fix", "running", now(), now()))
    from backend.patches import Patches
    patches = Patches(store)
    for name in ["a.txt", "b.txt"]:
        (root / name).write_text("before", encoding="utf-8")
    patch = patches.propose(store.one("tasks", task_id), [{"path": name, "base_hash": digest("before"), "content": "after"} for name in ["a.txt", "b.txt"]])
    (root / "b.txt").write_text("external", encoding="utf-8")
    with pytest.raises(Conflict):
        patches.apply(patch["id"])
    assert (root / "a.txt").read_text() == "before"
    # Simulate a crash between two per-file replacements, then recover the checkpoint.
    (root / "b.txt").write_text("before", encoding="utf-8")
    (root / "a.txt").write_text("after", encoding="utf-8")
    store.execute("UPDATE patches SET status='applying' WHERE id=?", (patch["id"],))
    restarted = Store(tmp_path / "state.sqlite3")
    restarted.recover()
    assert restarted.one("tasks", task_id)["status"] == "interrupted"
    assert restarted.one("patches", patch["id"])["status"] == "recovery_required"
    Patches(restarted).apply(patch["id"], undo=True)
    assert all((root / name).read_text() == "before" for name in ["a.txt", "b.txt"])


def test_cancel_running_task_and_reject_pending_patch(tmp_path, headers):
    app, script = configured_app(tmp_path, ["wait"])
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        task_id = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "explain"}).json()["id"]
        wait_task(client, task_id, "running")
        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.json()["status"] == "cancelled"
        script.append(action("propose_patch", changes=[{"path": "new.txt", "base_hash": "missing", "content": "new"}]))
        task_id = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "create"}).json()["id"]
        task = wait_task(client, task_id, "waiting_review")
        patch_id = task["patches"][0]["id"]
        assert client.post(f"/api/patches/{patch_id}/review", json={"accept": False}).json()["status"] == "rejected"
        assert not (root / "new.txt").exists()


async def test_cancel_before_coroutine_starts(tmp_path):
    store = Store(tmp_path / "state.sqlite3")
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", ("w", str(tmp_path), "workspace"))
    runtime = Runtime(store, Settings(store, persist_secrets=False), lambda: ScriptedModel(deque(["wait"])))
    task = runtime.create({"workspace_id": "w", "prompt": "queued"})
    await runtime.cancel(task["id"])
    assert store.one("tasks", task["id"])["status"] == "cancelled"
    await runtime.close()


def test_cumulative_step_budget_survives_review(tmp_path, headers):
    app, _ = configured_app(tmp_path, [action("propose_patch", changes=[{"path": "new.txt", "base_hash": "missing", "content": "new"}])])
    app.state.store.set_settings({"max_steps": 1})
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        task_id = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "create"}).json()["id"]
        paused = wait_task(client, task_id, "waiting_review")
        client.post(f"/api/patches/{paused['patches'][0]['id']}/review", json={"accept": True})
        complete = wait_task(client, task_id, "budget_exhausted")
        assert complete["steps"] == 1 and (root / "new.txt").read_text() == "new"
        assert complete["elapsed"] >= 0


def test_context_keeps_original_request_after_long_history():
    messages = [{"role": "system", "content": "policy"}] + [{"role": "user", "content": "old" * 10_000} for _ in range(30)]
    result = context_messages(messages, {"prompt": "important original request", "selected_file": "app.py", "test_argv": "[]"})
    assert "important original request" in result[1]["content"]
    assert sum(len(item["content"]) for item in result) < 56_000


def test_pending_review_can_resume_after_service_restart(tmp_path, headers):
    app, _ = configured_app(tmp_path, [action("propose_patch", changes=[{"path": "new.txt", "base_hash": "missing", "content": "reviewed"}])])
    with TestClient(app, headers=headers) as client:
        root, workspace_id = open_workspace(client, tmp_path)
        task_id = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "create"}).json()["id"]
        paused = wait_task(client, task_id, "waiting_review")
        patch_id = paused["patches"][0]["id"]
    resumed, _ = configured_app(tmp_path, [action("final", message="done")])
    with TestClient(resumed, headers=headers) as client:
        assert client.get(f"/api/tasks/{task_id}").json()["status"] == "waiting_review"
        assert not (root / "new.txt").exists()
        assert client.post(f"/api/patches/{patch_id}/review", json={"accept": True}).status_code == 200
        wait_task(client, task_id, "completed")
        assert (root / "new.txt").read_text() == "reviewed"


def test_nested_workspace_git_diff_filters_private_files(tmp_path):
    import shutil
    import subprocess
    if not shutil.which("git"):
        pytest.skip("Git not installed")
    root = tmp_path / "repo"
    nested = root / "nested"
    nested.mkdir(parents=True)

    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)

    git("init")
    (nested / "code.py").write_bytes(b"value = 1\n")
    (nested / ".env").write_bytes(b"KEY=before\n")
    (nested / "secret.pfx").write_bytes(b"before\n")
    git("add", ".")
    git("-c", "user.name=Local test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "commit", "-m", "test baseline")
    (nested / "code.py").write_bytes(b"value = 2\n")
    (nested / ".env").write_bytes(b"KEY=do-not-expose\n")
    (nested / "secret.pfx").write_bytes(b"do-not-expose\n")
    result = Workspace(str(nested)).git_diff()
    assert "+value = 2" in result
    assert "do-not-expose" not in result and ".env" not in result and ".pfx" not in result


def test_settings_never_store_key_in_sqlite(tmp_path, headers):
    app, _ = configured_app(tmp_path, [])
    with TestClient(app, headers=headers) as client:
        response = client.put("/api/settings", json={"model": "local-model", "base_url": "http://127.0.0.1:12345/v1", "api_key": "secret-test-key"})
        assert response.status_code == 200 and response.json()["has_api_key"]
        assert "secret-test-key" not in json.dumps(response.json())
        assert "secret-test-key" not in (tmp_path / "data/state.sqlite3").read_bytes().decode("latin1")
        assert "api_key" not in app.state.store.settings()


def test_analysis_ignores_legacy_wall_time_limit_and_keeps_step_budget(tmp_path, headers):
    class SlowModel:
        async def generate(self, messages, emit):
            await asyncio.sleep(.05)
            return action("final", message="不限任务时长，解析已完成。")

        def close(self):
            pass

    app = create_app(tmp_path / "data", token="test-token", model_factory=SlowModel, persist_secrets=False)
    app.state.store.set_settings({"task_timeout": .001, "max_steps": 1})
    with TestClient(app, headers=headers) as client:
        _, workspace_id = open_workspace(client, tmp_path)
        created = client.post("/api/tasks", json={"workspace_id": workspace_id, "prompt": "解析项目"}).json()
        complete = wait_task(client, created["id"], "completed")
        assert complete["steps"] == 1 and complete["elapsed"] >= .05


async def test_real_command_timeout_and_cancellation_stop_process(tmp_path):
    (tmp_path / "test_sleep.py").write_text("import os, time\nfrom pathlib import Path\ndef test_sleep():\n    Path('pid.txt').write_text(str(os.getpid()))\n    time.sleep(30)\n", encoding="utf-8")

    async def emit(*args):
        pass

    timed = await run_command(["python", "-m", "pytest", "-q"], tmp_path, emit, timeout=1)
    assert timed["timed_out"]
    pid_path = tmp_path / "pid.txt"
    if pid_path.exists():
        pid_path.unlink()
    job = asyncio.create_task(run_command(["python", "-m", "pytest", "-q"], tmp_path, emit))
    for _ in range(200):
        if pid_path.exists():
            break
        await asyncio.sleep(0.025)
    assert pid_path.exists()
    pid = int(pid_path.read_text())
    job.cancel()
    with pytest.raises(asyncio.CancelledError):
        await job
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            assert exit_code.value != 259  # STILL_ACTIVE
    else:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_workspace_rejects_symlink_outside_root(tmp_path):
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        # Windows directory junctions exercise the same resolved-path boundary.
        import subprocess
        command = f'New-Item -ItemType Junction -Path "{link}" -Target "{outside}" | Out-Null'
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True)
    with pytest.raises(ValueError):
        Workspace(str(root)).read("link/secret.txt")
    assert all(entry["name"] != "link" for entry in Workspace(str(root)).tree())
