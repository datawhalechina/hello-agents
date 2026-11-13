"""Durable progress, exact large-source pages and explicit coverage exceptions."""
from __future__ import annotations

import json

import pytest

from backend.annotation_progress import AnnotationProgress, PAGE_CHARS, SNAPSHOT_CHARS, encoded_size
from backend.store import Store, identifier, now
from backend.workspace import MAX_FILE, Workspace, digest


HEADER = ("# 代码用途：提供相加计算。\n# 输入文件：无。\n# 输入说明：接收两个数值。\n"
          "# 输出文件：无。\n# 输出说明：返回相加结果。\n")
COMMENTS = "# 函数用途：计算相加结果。\n# 输入说明：a：第一个数；b：第二个数。\n# 输出说明：返回两个数的和。\n"
BEFORE = "def add(a, b):\n    return a + b\n"
AFTER = HEADER + COMMENTS + BEFORE


@pytest.fixture
def ledger(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    store = Store(tmp_path / "service" / "state.sqlite3")
    workspace_id, session_id, task_id = identifier(), identifier(), identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "workspace"))
    store.execute("INSERT INTO sessions VALUES(?,?,?,?)", (session_id, workspace_id, "session", now()))
    store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                  (task_id, session_id, workspace_id, "注释", "running", now(), now()))
    return root, store, task_id, Workspace(str(root), include_build_sources=True)


def test_inventory_walks_once_and_repeated_pages_do_not_advance(ledger, monkeypatch):
    root, store, task_id, workspace = ledger
    for index in range(205):
        (root / f"module_{index:03}.py").write_text(BEFORE, encoding="utf-8", newline="")
    (root / ".env").write_text("SECRET=never_read", encoding="utf-8", newline="")
    (root / "private.key").write_text("secret", encoding="utf-8", newline="")
    walk, calls = workspace.files, []
    def counted(*, limit):
        calls.append(limit)
        return walk(limit=limit)
    monkeypatch.setattr(workspace, "files", counted)
    progress = AnnotationProgress(store, task_id, workspace)
    token = progress.token()
    first = progress.inventory({})
    assert first["total"] == 205 and len(first["files"]) == 100 and first["next_offset"] == 100
    assert progress.token() != token
    token = progress.token()
    assert progress.inventory({}) == first and progress.token() == token
    assert progress.inventory({"offset": 100})["next_offset"] == 200
    assert progress.inventory({"offset": 200})["next_offset"] is None
    assert progress.inventory({"offset": 999})["files"] == []
    assert calls == [None]
    restarted = AnnotationProgress(store, task_id, workspace)
    token = restarted.token()
    restarted.inventory({})
    assert restarted.token() == token and calls == [None, None]
    assert ".env" not in json.dumps(progress.snapshot())


def test_inventory_sliding_offsets_do_not_count_already_delivered_files_as_progress(ledger):
    root, store, task_id, workspace = ledger
    for index in range(40):
        (root / f"module_{index:03}.py").write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.inventory({"offset": 0})
    token = progress.token()
    for offset in (1, 2, 3, 20, 39, 40):
        progress.inventory({"offset": offset})
        assert progress.token() == token
    # Previously delivered coverage survives a resume, independent of offsets.
    restarted = AnnotationProgress(store, task_id, workspace)
    assert restarted.token() == token
    restarted.inventory({"offset": 4})
    assert restarted.token() == token


def test_inventory_overlap_counts_only_new_paths_and_new_pages_advance(ledger):
    root, store, task_id, workspace = ledger
    for index in range(205):
        (root / f"module_{index:03}.py").write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.inventory({"offset": 0})
    token = progress.token()
    progress.inventory({"offset": 50})  # Adds paths 100..149.
    assert progress.token() != token
    token = progress.token()
    progress.inventory({"offset": 25})  # All 100 returned paths were delivered.
    assert progress.token() == token
    progress.inventory({"offset": 150})  # Adds the remaining 55 actual files.
    assert progress.token() != token


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_large_python_pages_preserve_source_and_hash_and_resume_cursor(ledger, newline):
    root, store, task_id, workspace = ledger
    content = newline.join(f"value_{i} = {i}  # 实际源文件" for i in range(2200)) + newline
    assert len(content) > 51_000
    (root / "large.py").write_bytes(content.encode("utf-8"))
    progress = AnnotationProgress(store, task_id, workspace)
    first = progress.read({"path": "large.py"})
    assert first["start_line"] == 1 and first["next_start_line"] > 1
    assert not first["fully_read"] and progress.read_baselines["large.py"] == digest(content)
    observed = [first["content"]]
    cursor = first["next_start_line"]
    # On resume, saved ranges and implicit cursor survive without fake reads.
    progress = AnnotationProgress(store, task_id, workspace)
    assert not progress.read_baselines
    while cursor:
        page = progress.read({"path": "large.py"})
        assert page["start_line"] == cursor
        assert page["hash"] == digest(content) and encoded_size(page) <= PAGE_CHARS
        assert "自动接续" in page["message"]
        observed.append(page["content"])
        cursor = page["next_start_line"]
    assert "".join(observed) == content
    assert page["fully_read"] and progress.fully_read("large.py", digest(content))
    next_file = progress.snapshot()["next_files"][0]
    assert next_file["fully_read"] and next_file["next_action"] == "propose_patch"
    assert next_file["next_start_line"] is None
    token = progress.token()
    again = progress.read({"path": "large.py"})
    assert again["start_line"] == 1 and again["content"] == first["content"]
    assert progress.token() == token


def test_json_escaping_is_measured_before_page_delivery(ledger):
    root, store, task_id, workspace = ledger
    # Most input characters need JSON escaping; a raw 18k cut would overflow.
    content = ("item = " + repr("\\\"" * 80) + "\r\n") * 160
    (root / "quoted.py").write_bytes(content.encode("utf-8"))
    progress = AnnotationProgress(store, task_id, workspace)
    page = progress.read({"path": "quoted.py"})
    assert page["next_start_line"] is not None and encoded_size(page) <= PAGE_CHARS
    assert page["content"] == "".join(content.splitlines(keepends=True)[:page["end_line"]])
    assert len(json.dumps(page, ensure_ascii=False)) <= PAGE_CHARS


def test_explicit_ranges_only_count_new_coverage(ledger):
    root, store, task_id, workspace = ledger
    content = "".join(f"line_{i} = {i}\n" for i in range(30))
    (root / "source.py").write_text(content, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    page = progress.read({"path": "source.py", "start_line": 11, "end_line": 20})
    assert page["content"] == "".join(content.splitlines(keepends=True)[10:20])
    token = progress.token()
    progress.read({"path": "source.py", "start_line": 12, "end_line": 15})
    assert progress.token() == token and not progress.fully_read("source.py", digest(content))
    progress.read({"path": "source.py", "end_line": 10})
    page = progress.read({"path": "source.py"})
    assert page["start_line"] == 21 and page["fully_read"]
    assert progress.state["files"]["source.py"]["ranges"] == [[1, 30]]


def test_complete_python_is_verified_without_rewriting_and_force_can_read(ledger):
    root, store, task_id, workspace = ledger
    (root / "done.py").write_text(AFTER, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    result = progress.read({"path": "done.py"})
    assert result["status"] == "verified" and result["content"] == AFTER
    assert result["format_verified"] and "含义" in result["format_note"]
    assert "already_complete" not in result
    assert progress.snapshot()["counts"]["verified"] == 1
    token = progress.token()
    assert progress.read({"path": "done.py"})["already_complete"] and progress.token() == token
    forced = progress.read({"path": "done.py", "force": True})
    assert forced["content"] == AFTER and forced["fully_read"]
    assert (root / "done.py").read_text(encoding="utf-8") == AFTER


def test_complete_format_long_python_delivers_every_source_page_before_compacting(ledger):
    root, store, task_id, workspace = ledger
    content = AFTER + "# 保留原有实现与说明，仍需核对含义。\n" * 2200
    (root / "complete_long.py").write_text(content, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    page = progress.read({"path": "complete_long.py"})
    assert page["status"] == "reading" and page["content"]
    assert page["format_verified"] and page["next_start_line"] is not None
    assert progress.snapshot()["counts"]["verified"] == 0
    parts = [page["content"]]
    # Restart halfway through must not turn a format check into semantic approval.
    progress = AnnotationProgress(store, task_id, workspace)
    while page["next_start_line"] is not None:
        page = progress.read({"path": "complete_long.py"})
        parts.append(page["content"])
        assert page["content"] and not page.get("already_complete")
    assert "".join(parts) == content and page["status"] == "verified"
    assert progress.read({"path": "complete_long.py"})["already_complete"]


def test_reconcile_invalidates_completed_source_changed_or_removed_during_same_run(ledger):
    root, store, task_id, workspace = ledger
    for name in ("changed.py", "removed.py"):
        (root / name).write_text(AFTER, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.read({"path": "changed.py"})
    progress.read({"path": "removed.py"})
    assert progress.snapshot()["counts"]["verified"] == 2
    (root / "changed.py").write_text(BEFORE, encoding="utf-8", newline="")
    (root / "removed.py").unlink()
    progress.reconcile()
    snapshot = progress.snapshot()
    assert snapshot["counts"]["verified"] == 0
    assert snapshot["counts"]["pending"] == 1 and snapshot["counts"]["blocked"] == 1
    assert not progress.read_baselines
    assert progress.read({"path": "changed.py"})["content"] == BEFORE


def test_reconcile_refresh_inventory_discovers_new_sources_once_at_final(ledger, monkeypatch):
    root, store, task_id, workspace = ledger
    (root / "original.py").write_text(AFTER, encoding="utf-8", newline="")
    walk, calls = workspace.files, []
    def counted(*, limit):
        calls.append(limit)
        return walk(limit=limit)
    monkeypatch.setattr(workspace, "files", counted)
    progress = AnnotationProgress(store, task_id, workspace)
    progress.read({"path": "original.py"})
    (root / "new.py").write_text(BEFORE, encoding="utf-8", newline="")
    progress.reconcile()
    assert calls == [None] and progress.snapshot()["counts"]["total"] == 1
    progress.reconcile(refresh_inventory=True)
    assert calls == [None, None]
    assert progress.snapshot()["counts"]["total"] == 2
    assert progress.snapshot()["next_files"][0]["path"] == "new.py"
    progress.inventory({})
    assert calls == [None, None]


def test_legacy_format_only_verified_ledger_is_downgraded_until_source_read(ledger):
    root, store, task_id, workspace = ledger
    (root / "legacy.py").write_text(AFTER, encoding="utf-8", newline="")
    old = {"revision": 1, "files": {"legacy.py": {"status": "verified", "hash": digest(AFTER), "checked": True}},
           "inventory_pages": []}
    store.execute("INSERT INTO annotation_progress(task_id,state) VALUES(?,?)", (task_id, json.dumps(old)))
    progress = AnnotationProgress(store, task_id, workspace)
    assert progress.snapshot()["counts"]["verified"] == 0
    result = progress.read({"path": "legacy.py"})
    assert result["content"] == AFTER and result["format_verified"] and result["status"] == "verified"


def test_python_format_verification_does_not_imply_semantic_accuracy(ledger):
    root, store, task_id, workspace = ledger
    (root / "done.py").write_text(AFTER, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.read({"path": "done.py"})
    assert "格式" in progress.snapshot()["message"] and "语义" in progress.snapshot()["message"]


def test_external_edit_invalidates_finished_hash_on_resume_and_read(ledger):
    root, store, task_id, workspace = ledger
    source = root / "done.py"
    source.write_text(AFTER, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.read({"path": "done.py"})
    source.write_text(BEFORE, encoding="utf-8", newline="")
    restarted = AnnotationProgress(store, task_id, workspace)
    assert restarted.snapshot()["counts"]["verified"] == 0
    assert restarted.snapshot()["next_files"][0]["path"] == "done.py"
    fresh = restarted.read({"path": "done.py"})
    assert fresh["content"] == BEFORE and fresh["hash"] == digest(BEFORE)
    source.write_text(AFTER, encoding="utf-8", newline="")
    assert restarted.read({"path": "done.py"})["status"] == "verified"


def test_applied_patch_ledger_uses_real_hash_and_distinguishes_other_languages(ledger):
    root, store, task_id, workspace = ledger
    python, javascript = root / "done.py", root / "done.js"
    python.write_text(AFTER, encoding="utf-8", newline="")
    javascript.write_text("// 说明\nconst value = 1;\n", encoding="utf-8", newline="")
    changes = [{"path": "done.py", "after_hash": digest(AFTER)},
               {"path": "done.js", "after_hash": digest(javascript.read_text(encoding="utf-8"))}]
    workspace_id = store.one("tasks", task_id)["workspace_id"]
    store.execute("INSERT INTO patches VALUES(?,?,?,?,?,?)",
                  (identifier(), task_id, workspace_id, "applied", json.dumps(changes), now()))
    progress = AnnotationProgress(store, task_id, workspace)
    assert progress.snapshot()["counts"]["verified"] == 1
    assert progress.snapshot()["counts"]["applied"] == 1
    assert not progress.read_baselines
    assert progress.read({"path": "done.js"})["status"] == "applied"
    javascript.write_text("const value = 2;\n", encoding="utf-8", newline="")
    python.write_text(BEFORE, encoding="utf-8", newline="")
    restarted = AnnotationProgress(store, task_id, workspace)
    assert restarted.snapshot()["counts"]["verified"] == 0
    assert restarted.snapshot()["counts"]["applied"] == 0


def test_undone_patch_is_not_recovered_as_completed(ledger):
    root, store, task_id, workspace = ledger
    (root / "source.js").write_text("// annotated\nconst value = 1;\n", encoding="utf-8", newline="")
    changes = [{"path": "source.js", "after_hash": digest("// annotated\nconst value = 1;\n")}]
    workspace_id = store.one("tasks", task_id)["workspace_id"]
    store.execute("INSERT INTO patches VALUES(?,?,?,?,?,?)",
                  (identifier(), task_id, workspace_id, "undone", json.dumps(changes), now()))
    progress = AnnotationProgress(store, task_id, workspace)
    assert progress.snapshot()["counts"]["applied"] == 0


def test_applied_clears_old_read_ranges_and_rejects_unmatched_after_hash(ledger):
    root, store, task_id, workspace = ledger
    source = root / "source.py"
    source.write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.read({"path": "source.py"})
    source.write_text(AFTER, encoding="utf-8", newline="")
    progress.applied({"changes": [{"path": "source.py", "after_hash": "forged"}]})
    assert progress.state["files"]["source.py"]["status"] == "reading"
    progress.applied({"changes": [{"path": "source.py", "after_hash": digest(AFTER)}]})
    assert progress.state["files"]["source.py"]["status"] == "verified"
    assert not progress.fully_read("source.py", digest(AFTER)) and "source.py" not in progress.read_baselines


def test_documents_are_skipped_but_readable_and_binary_missing_large_are_explicit(ledger):
    root, store, task_id, workspace = ledger
    (root / "README.md").write_text("# 项目说明\n", encoding="utf-8", newline="")
    (root / "data.json").write_text('{"version":1}', encoding="utf-8", newline="")
    (root / "opaque.dat").write_bytes(b"\x00binary")
    (root / "huge.py").write_bytes(b"#" * (MAX_FILE + 1))
    progress = AnnotationProgress(store, task_id, workspace)
    assert progress.read({"path": "README.md"})["status"] == "skipped"
    assert progress.read({"path": "data.json"})["content"] == '{"version":1}'
    assert progress.read({"path": "opaque.dat"})["status"] == "blocked"
    assert progress.read({"path": "missing.py"})["status"] == "blocked"
    token = progress.token()
    progress.read({"path": "missing.py"})
    assert progress.token() == token
    snapshot = progress.snapshot()
    assert snapshot["counts"]["blocked"] == 2
    assert {item["path"] for item in snapshot["blocked"]} == {"huge.py", "opaque.dat"}


def test_invented_missing_paths_do_not_advance_or_fill_ledger_but_real_new_reads_do(ledger):
    root, store, task_id, workspace = ledger
    source = root / "existing.py"
    source.write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    token = progress.token()
    for index in range(15):
        result = progress.read({"path": f"missing_{index}.py"})
        assert result["status"] == "blocked" and progress.token() == token
    assert len(progress.state["files"]) == 1
    # A cached project file disappearing is a real discovered blockage.
    source.unlink()
    assert progress.read({"path": "existing.py"})["status"] == "blocked"
    assert progress.token() != token
    token = progress.token()
    (root / "new.py").write_text(BEFORE, encoding="utf-8", newline="")
    result = progress.read({"path": "new.py"})
    assert result["content"] == BEFORE and progress.token() != token
    assert progress.state["files"]["new.py"]["status"] == "reading"


def test_single_oversized_line_is_not_truncated_or_returned_as_source(ledger):
    root, store, task_id, workspace = ledger
    content = "long_value = '" + "\\\"" * 10_000 + "'\n"
    (root / "line.py").write_text(content, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    first = progress.read({"path": "line.py"})
    assert first["status"] == "blocked" and "content" not in first and "单行" in first["error"]
    assert not progress.fully_read("line.py", digest(content))
    token = progress.token()
    progress.read({"path": "line.py"})
    assert progress.token() == token


@pytest.mark.parametrize("original", [b"\x00binary", b"#" * (MAX_FILE + 1), b"x = '" + b"a" * 20_000 + b"'\n"],
                         ids=["binary", "too_large", "long_line"])
def test_blocked_file_can_be_repaired_between_runs(ledger, original):
    root, store, task_id, workspace = ledger
    source = root / "broken.py"
    source.write_bytes(original)
    progress = AnnotationProgress(store, task_id, workspace)
    assert progress.read({"path": "broken.py"})["status"] == "blocked"
    source.write_bytes(BEFORE.encode("utf-8"))
    restarted = AnnotationProgress(store, task_id, workspace)
    assert restarted.snapshot()["next_files"][0]["path"] == "broken.py"
    assert restarted.read({"path": "broken.py"})["content"] == BEFORE


@pytest.mark.parametrize("args", [{"start_line": 0}, {"start_line": True}, {"end_line": -1},
                                  {"start_line": 2, "end_line": 1}, {"force": "true"}, {"start_line": 999}])
def test_bad_page_arguments_are_rejected(ledger, args):
    root, store, task_id, workspace = ledger
    (root / "file.py").write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    with pytest.raises(ValueError):
        progress.read({"path": "file.py", **args})


@pytest.mark.parametrize("path", ["../outside.py", ".env", "private.key"])
def test_unsafe_read_paths_never_enter_ledger(ledger, path):
    _, store, task_id, workspace = ledger
    progress = AnnotationProgress(store, task_id, workspace)
    with pytest.raises(ValueError):
        progress.read({"path": path})
    assert not progress.state["files"] and not progress.read_baselines


def test_inventory_and_snapshot_stay_bounded_with_long_paths(ledger, monkeypatch):
    _, store, task_id, workspace = ledger
    paths = [f"{'long_directory/' * 25}{i}.py" for i in range(110)]
    monkeypatch.setattr(workspace, "files", lambda limit=None: iter(paths))
    progress = AnnotationProgress(store, task_id, workspace)
    page = progress.inventory({})
    assert len(page["files"]) < 100 and encoded_size(page) <= PAGE_CHARS
    assert page["next_offset"] == len(page["files"])
    observed = list(page["files"])
    while page["next_offset"] is not None:
        page = progress.inventory({"offset": page["next_offset"]})
        observed.extend(page["files"])
    assert observed == paths
    assert encoded_size(progress.snapshot()) <= SNAPSHOT_CHARS


def test_deleted_task_progress_is_removed_and_late_thread_cannot_recreate_it(ledger):
    root, store, task_id, workspace = ledger
    (root / "source.py").write_text(BEFORE, encoding="utf-8", newline="")
    progress = AnnotationProgress(store, task_id, workspace)
    progress.inventory({})
    assert store.rows("SELECT * FROM annotation_progress WHERE task_id=?", (task_id,))
    store.delete_task(task_id)
    assert not store.rows("SELECT * FROM annotation_progress WHERE task_id=?", (task_id,))
    progress.read({"path": "source.py"})
    assert not store.rows("SELECT * FROM annotation_progress WHERE task_id=?", (task_id,))
    assert (root / "source.py").read_text(encoding="utf-8") == BEFORE


def test_late_cancelled_worker_cannot_overwrite_a_resumed_run_ledger(ledger):
    root, store, task_id, workspace = ledger
    for name in ("old.py", "new.py"):
        (root / name).write_text(BEFORE, encoding="utf-8", newline="")
    old_worker = AnnotationProgress(store, task_id, workspace)
    resumed = AnnotationProgress(store, task_id, workspace)
    resumed.read({"path": "new.py"})
    before_late_write = store.rows("SELECT state FROM annotation_progress WHERE task_id=?", (task_id,))[0]["state"]
    old_worker.read({"path": "old.py"})
    old_worker.inventory({})
    after_late_write = store.rows("SELECT state FROM annotation_progress WHERE task_id=?", (task_id,))[0]["state"]
    assert after_late_write == before_late_write
    durable = json.loads(after_late_write)
    assert durable["files"]["new.py"]["status"] == "reading"
    assert durable["files"]["old.py"]["status"] == "pending"
    assert durable["owner"] == resumed.owner and old_worker.owner != resumed.owner
