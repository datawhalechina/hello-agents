"""A fixed documentation bundle previews, applies and restores real PNG bytes."""
from __future__ import annotations

import base64
import copy
import io
import json
import random

import pytest
from PIL import Image

from backend.patches import DOCUMENTATION_PATHS, DOCUMENTATION_SKILL, Patches, raw_digest
from backend.skills import ANNOTATION_SKILL
from backend.store import Store, identifier, now
from backend.workspace import Conflict


def png(color="blue", size=(80, 50)):
    data = io.BytesIO()
    Image.new("RGB", size, color).save(data, format="PNG")
    return data.getvalue()


@pytest.fixture
def service(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    store = Store(tmp_path / "state.sqlite3")
    workspace_id, task_id = identifier(), identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "project"))
    store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (task_id, identifier(), workspace_id, "说明与设计图", "waiting_review", DOCUMENTATION_SKILL, now(), now()))
    return root, store, store.one("tasks", task_id), Patches(store)


def bundle(root, color="blue"):
    changes = []
    for relative in DOCUMENTATION_PATHS:
        path = root / relative
        values = {"path": relative, "base_hash": raw_digest(path.read_bytes() if path.exists() else None)}
        if relative.endswith(".png"):
            values.update(content=base64.b64encode(png(color)).decode(), encoding="base64", mime_type="image/png")
        else:
            values["content"] = f"# {relative}\n\n真实项目说明。\n"
        changes.append(values)
    return changes


def test_restart_preserves_pending_document_review_and_all_five_changes(service):
    root, store, task, patches = service
    proposed = patches.propose_documentation(task, bundle(root))
    restarted = Store(store.path)
    restarted.recover()
    assert restarted.one('tasks', task['id'])['status'] == 'waiting_review'
    assert Patches(restarted).get(proposed['id']) == proposed
    assert all(not (root / path).exists() for path in DOCUMENTATION_PATHS)


def test_proposed_bundle_is_one_reviewable_patch_and_does_not_write_before_approval(service):
    root, store, task, patches = service
    patch = patches.propose_documentation(task, bundle(root))
    assert patch["status"] == "proposed" and len(patch["changes"]) == 5
    assert not list(root.iterdir())
    assert len(store.rows("SELECT id FROM patches")) == 1
    for change in patch["changes"]:
        assert change["before"] is None and change["before_hash"] == "missing"
        if change["path"].endswith(".png"):
            assert change["encoding"] == "base64" and change["mime_type"] == "image/png"
            assert change["diff"] == ""
            assert base64.b64decode(change["after"]).startswith(b"\x89PNG\r\n\x1a\n")
        else:
            assert "真实项目说明" in change["diff"]
    applied = patches.apply(patch["id"])
    assert applied["status"] == "applied"
    for relative in DOCUMENTATION_PATHS:
        assert (root / relative).is_file()
    assert (root / DOCUMENTATION_PATHS[2]).read_bytes() == png()
    assert patches.apply(patch["id"], undo=True)["status"] == "reverted"
    assert not any((root / relative).exists() for relative in DOCUMENTATION_PATHS)


def test_overwritten_png_and_markdown_restore_exact_original_bytes(service):
    root, _, task, patches = service
    old = {}
    for relative in DOCUMENTATION_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        value = png("red") if relative.endswith(".png") else "# 旧说明\r\n保留原换行\r\n".encode()
        path.write_bytes(value)
        old[relative] = value
    untouched = root / "README.md"
    untouched.write_bytes(b"keep me\n")
    patch = patches.propose_documentation(task, bundle(root))
    patches.apply(patch["id"])
    assert (root / DOCUMENTATION_PATHS[2]).read_bytes() == png()
    patches.apply(patch["id"], undo=True)
    assert all((root / relative).read_bytes() == raw for relative, raw in old.items())
    assert untouched.read_bytes() == b"keep me\n"


def test_png_optimistic_conflicts_prevent_partial_apply_and_undo(service):
    root, _, task, patches = service
    patch = patches.propose_documentation(task, bundle(root))
    image = root / DOCUMENTATION_PATHS[2]
    image.parent.mkdir(parents=True)
    image.write_bytes(png("green"))
    with pytest.raises(Conflict, match="其他操作修改"):
        patches.apply(patch["id"])
    assert not (root / DOCUMENTATION_PATHS[0]).exists()
    image.unlink()
    patches.apply(patch["id"])
    image.write_bytes(png("green"))
    with pytest.raises(Conflict, match="其他操作修改"):
        patches.apply(patch["id"], undo=True)
    assert (root / DOCUMENTATION_PATHS[0]).is_file()
    assert image.read_bytes() == png("green")


def test_existing_large_png_can_be_reviewed_replaced_and_restored(service):
    root, _, task, patches = service
    target = root / DOCUMENTATION_PATHS[2]
    target.parent.mkdir(parents=True)
    original = io.BytesIO()
    Image.frombytes("RGB", (400, 400), random.Random(9).randbytes(400 * 400 * 3)).save(original, "PNG")
    old = original.getvalue()
    assert len(old) > 256_000
    target.write_bytes(old)
    patch = patches.propose_documentation(task, bundle(root))
    assert base64.b64decode(patch["changes"][2]["before"]) == old
    patches.apply(patch["id"])
    assert target.read_bytes() == png()
    patches.apply(patch["id"], undo=True)
    assert target.read_bytes() == old


def test_changed_baseline_refuses_the_entire_bundle_before_checkpoint(service):
    root, store, task, patches = service
    changes = bundle(root)
    path = root / DOCUMENTATION_PATHS[2]
    path.parent.mkdir(parents=True)
    path.write_bytes(png("green"))
    with pytest.raises(Conflict, match="基线已变化"):
        patches.propose_documentation(task, changes)
    assert not store.rows("SELECT id FROM patches")
    assert not (root / DOCUMENTATION_PATHS[0]).exists()


def test_mid_write_failure_restores_text_and_binary_and_review_checkpoint(service, monkeypatch):
    root, _, task, patches = service
    for relative in DOCUMENTATION_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png("red") if relative.endswith(".png") else b"old text\r\n")
    old = {relative: (root / relative).read_bytes() for relative in DOCUMENTATION_PATHS}
    patch = patches.propose_documentation(task, bundle(root))
    original_write = Patches.write
    calls = 0

    def fail_fourth(path, content, mode=None):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("simulated write failure")
        return original_write(path, content, mode)

    monkeypatch.setattr(Patches, "write", staticmethod(fail_fourth))
    with pytest.raises(OSError, match="simulated"):
        patches.apply(patch["id"])
    assert all((root / relative).read_bytes() == value for relative, value in old.items())
    assert patches.get(patch["id"])["status"] == "proposed"


def test_restart_recovers_a_partial_binary_checkpoint_without_deleting_unrelated_files(service):
    root, store, task, patches = service
    patch = patches.propose_documentation(task, bundle(root))
    for change in patch["changes"][:3]:
        target = root / change["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(change["after"]) if change.get("encoding") else change["after"].encode())
    store.execute("UPDATE patches SET status='applying' WHERE id=?", (patch["id"],))
    untouched = root / "source.py"
    untouched.write_bytes(b"value = 1\n")
    restarted = Store(store.path)
    restarted.recover()
    recovered = Patches(restarted)
    assert recovered.get(patch["id"])["status"] == "recovery_required"
    recovered.apply(patch["id"], undo=True)
    assert not any((root / relative).exists() for relative in DOCUMENTATION_PATHS)
    assert untouched.read_bytes() == b"value = 1\n"


@pytest.mark.parametrize("corruption", ["escape", "alias", "duplicate", "extra", "missing", "delete", "badbase64", "fakepng", "mime", "encoding", "oversized"])
def test_invalid_output_bundle_cannot_write_or_leave_a_checkpoint(service, corruption):
    root, store, task, patches = service
    changes = bundle(root)
    if corruption == "escape": changes[0]["path"] = "../项目说明.md"
    elif corruption == "alias": changes[2]["path"] = "docs/diagrams/../diagrams/architecture.png"
    elif corruption == "duplicate": changes[1]["path"] = changes[0]["path"]
    elif corruption == "extra": changes.append(copy.deepcopy(changes[0]))
    elif corruption == "missing": changes.pop()
    elif corruption == "delete": changes[0]["content"] = None
    elif corruption == "badbase64": changes[2]["content"] = "not base64!"
    elif corruption == "fakepng": changes[2]["content"] = base64.b64encode(b"not a PNG").decode()
    elif corruption == "mime": changes[2]["mime_type"] = "image/svg+xml"
    elif corruption == "encoding": changes[2]["encoding"] = "utf-8"
    else: changes[2]["content"] = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 256_001).decode()
    with pytest.raises(ValueError): patches.propose_documentation(task, changes)
    assert not store.rows("SELECT id FROM patches")
    assert not list(root.iterdir())


@pytest.mark.parametrize("skill", [None, ANNOTATION_SKILL])
def test_other_tasks_cannot_use_documentation_binary_channel(service, skill):
    root, _, task, patches = service
    with pytest.raises(ValueError, match="只有项目解析"):
        patches.propose_documentation({**task, "skill": skill}, bundle(root))
    with pytest.raises(ValueError, match="普通补丁"):
        patches.propose({**task, "skill": skill}, [bundle(root)[2]])
    with pytest.raises(ValueError, match="PNG"):
        patches.propose({**task, "skill": skill}, [{"path": "docs/diagrams/architecture.png", "base_hash": "missing", "content": "plain text"}])


def test_analysis_tasks_cannot_use_generic_patch_to_modify_source(service):
    _, _, task, patches = service
    with pytest.raises(ValueError, match="普通源码补丁"):
        patches.propose(task, [{"path": "source.py", "base_hash": "missing", "content": "print('bad')"}])


@pytest.mark.parametrize("corruption", ["path", "data", "hash", "mime", "workspace", "non_analysis"])
def test_persisted_binary_record_is_revalidated_before_preview_or_apply(service, corruption):
    root, store, task, patches = service
    patch = patches.propose_documentation(task, bundle(root))
    changes = json.loads(store.one("patches", patch["id"])["changes"])
    if corruption == "path": changes[2]["path"] = "source.py"
    elif corruption == "data": changes[2]["after"] = base64.b64encode(b"fake").decode()
    elif corruption == "hash": changes[2]["after_hash"] = "0" * 64
    elif corruption == "mime": changes[2]["mime_type"] = "image/svg+xml"
    elif corruption == "workspace": store.execute("UPDATE patches SET workspace_id=? WHERE id=?", (identifier(), patch["id"]))
    else: store.execute("UPDATE tasks SET skill=NULL WHERE id=?", (task["id"],))
    store.execute("UPDATE patches SET changes=? WHERE id=?", (json.dumps(changes), patch["id"]))
    with pytest.raises(ValueError): patches.get(patch["id"])
    with pytest.raises(ValueError): patches.apply(patch["id"])
    assert not list(root.iterdir())


def test_oversized_png_dimensions_rejected_before_pixel_allocation(service):
    root, store, task, patches = service
    changes = bundle(root)
    changes[2]["content"] = base64.b64encode(png(size=(4097, 1))).decode()
    with pytest.raises(ValueError, match="尺寸"):
        patches.propose_documentation(task, changes)
    assert not store.rows("SELECT id FROM patches")
