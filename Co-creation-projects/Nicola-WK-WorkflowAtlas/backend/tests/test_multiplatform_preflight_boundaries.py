"""Multi-platform import confirmation, ambiguity and failure boundaries."""
import json

import pytest

from app.connectors.local import ImportValidationError, parse_messages
from test_platform_export_compatibility import (
    chatlab,
    commit_preview,
    forbid_import_network_and_analysis,
    raw_preview,
)


def activity(identifier="activity-1", **changes):
    return {"id": identifier, "time": "2026-11-12 09:00:00", "chat": "oc_synthetic", "sender": "虚构同事", "content": "接口开发计划确认", **changes}


@pytest.mark.parametrize("format", ["auto", "json", "txt"])
def test_corrupt_json_never_becomes_plain_chat_text(client, format):
    content = '[{"id":"synthetic","time":"2026-11-12 09:00:00","sender":"虚构同事","content":"PRIVATE-BROKEN"'
    preview, body, options = raw_preview(client, content, format=format)
    assert preview["valid"] == 0 and preview["messages"] == [] and preview["issues"]
    assert client.get("/api/messages").json() == []


def test_activity_bad_middle_record_does_not_hide_later_valid_record(client):
    rows = [activity("first"), activity("bad", time="PRIVATE-TIME-IS-NOT-A-DATE"), activity("last")]
    content = json.dumps(rows, ensure_ascii=False)
    preview, body, options = raw_preview(client, content)
    assert preview["total"] == 3 and preview["valid"] == 2
    assert [message["text"] for message in preview["messages"]] == [rows[0]["content"], rows[2]["content"]]
    assert {issue["position"] for issue in preview["issues"]} == {2}
    assert all("PRIVATE-TIME" not in issue["detail"] for issue in preview["issues"])
    with pytest.raises(ImportValidationError):
        parse_messages(content, options["source_id"], "auto", options["naive_timezone"])
    strict = client.post("/api/import/file", params=options, content=body)
    assert strict.status_code == 400 and client.get("/api/messages").json() == []
    result = commit_preview(client, preview, body, options)
    assert result["imported"] == 2 and result["warnings"]
    assert {message["id"] for message in client.get("/api/messages").json()} == {"first", "last"}


@pytest.mark.parametrize("row", [
    {"id": "no-time", "chat": "oc_synthetic", "sender": "虚构同事", "content": "没有原始时间"},
    {"sender": "虚构同事", "content": "没有结构标识和时间"},
    {"id": "ambiguous", "time": "2026-11-12 09:00:00", "timestamp": "2026-11-13 09:00:00", "sender": "虚构同事", "content": "两个时间字段矛盾"},
])
def test_missing_time_or_ambiguous_time_aliases_are_not_silently_repaired(client, row):
    preview, _, _ = raw_preview(client, json.dumps([row], ensure_ascii=False))
    assert preview["valid"] == 0 and preview["issues"] and preview["messages"] == []


def test_chatlab_declared_platform_cannot_override_embedded_source_identity(client):
    envelope = chatlab()
    envelope["messages"][0]["source_id"] = "different-source"
    preview, _, _ = raw_preview(client, json.dumps(envelope, ensure_ascii=False))
    assert preview["valid"] == 0 and preview["issues"]
    assert client.get("/api/messages").json() == []


@pytest.mark.parametrize("change", ["input", "timezone", "source", "format"])
def test_changed_multiplatform_input_or_options_invalidates_preview_fingerprint(client, change):
    content = json.dumps([activity()], ensure_ascii=False)
    preview, body, options = raw_preview(client, content)
    assert preview["valid"] == 1
    if change == "input":
        body = json.dumps([activity(content="变更后正文")], ensure_ascii=False).encode()
    elif change == "timezone":
        options["naive_timezone"] = "UTC"
    elif change == "source":
        options["source_id"] = "different-source"
    else:
        options["format"] = "json"
    response = client.post("/api/import/commit", params={**options, "fingerprint": preview["fingerprint"]}, content=body)
    assert response.status_code == 409
    assert client.get("/api/messages").json() == []


def test_changed_raw_record_same_platform_native_identity_is_conflict(client):
    first = chatlab()
    preview, body, options = raw_preview(client, json.dumps(first, ensure_ascii=False))
    assert preview["valid"] == 1
    commit_preview(client, preview, body, options)
    changed = chatlab(content="同一原始标识却出现不同正文")
    conflict, _, _ = raw_preview(client, json.dumps(changed, ensure_ascii=False))
    assert conflict["valid"] == 0 and conflict["issues"]
    assert any(issue["code"] == "immutable_conflict" for issue in conflict["issues"])
    assert client.get("/api/messages").json()[0]["text"] == first["messages"][0]["content"]


def test_repeated_chatlab_native_id_deduplicates_only_identical_observations(client):
    envelope = chatlab()
    envelope["messages"] *= 3
    preview, body, options = raw_preview(client, json.dumps(envelope, ensure_ascii=False))
    assert preview["total"] == 3 and preview["valid"] == 1 and preview["duplicates"] == 2
    assert preview["issues"] == []
    assert commit_preview(client, preview, body, options)["imported"] == 1
    repeated, _, _ = raw_preview(client, body)
    assert repeated["duplicates"] == 3 and repeated["imported_candidates"] == 0


def test_conflicting_chatlab_native_id_excludes_all_variants(client):
    envelope = chatlab()
    original = envelope["messages"][0]
    envelope["messages"] = [original, {**original, "content": "相同标识的另一版本"}]
    preview, _, _ = raw_preview(client, json.dumps(envelope, ensure_ascii=False))
    assert preview["total"] == 2 and preview["valid"] == 0
    assert {issue["position"] for issue in preview["issues"] if issue["code"] == "immutable_conflict"} == {1, 2}
    assert client.get("/api/messages").json() == []


@pytest.mark.parametrize("format,content", [
    ("csv", "id,time,sender,content\nfirst,2026-11-12 09:00:00,虚构作者,第一条\nbad,2026-99-99 09:00:00,虚构作者,无效时间\nlast,2026-11-12 09:10:00,虚构作者,最后一条\n"),
    ("txt", "2026-11-12 09:00:00 虚构作者(123456)\n第一条\n2026-99-99 09:00:00 虚构作者(123456)\n无效时间\n2026-11-12 09:10:00 虚构作者(123456)\n最后一条"),
    ("html", "<table><tr><th>id</th><th>time</th><th>sender</th><th>content</th></tr><tr><td>first</td><td>2026-11-12 09:00:00</td><td>虚构作者</td><td>第一条</td></tr><tr><td>bad</td><td>2026-99-99 09:00:00</td><td>虚构作者</td><td>无效时间</td></tr><tr><td>last</td><td>2026-11-12 09:10:00</td><td>虚构作者</td><td>最后一条</td></tr></table>"),
])
def test_each_text_adapter_reports_bad_middle_row_and_keeps_later_valid_rows(client, format, content):
    preview, body, options = raw_preview(client, content, format=format)
    assert preview["total"] == 3 and preview["valid"] == 2
    assert {issue["position"] for issue in preview["issues"]} == {2}
    assert [message["text"] for message in preview["messages"]] == ["第一条", "最后一条"]
    strict = client.post("/api/import/file", params=options, content=body)
    assert strict.status_code == 400 and client.get("/api/messages").json() == []
    assert commit_preview(client, preview, body, options)["imported"] == 2


def test_new_platform_file_preview_and_commit_do_not_start_jobs_or_create_facts(client):
    content = json.dumps(chatlab(), ensure_ascii=False)
    before = client.get("/api/stats").json()
    preview, body, options = raw_preview(client, content)
    assert client.get("/api/stats").json() == before
    commit_preview(client, preview, body, options)
    after = client.get("/api/stats").json()
    assert after["messages"] == before["messages"] + 1
    assert after["facts"] == before["facts"] == 0 and after["projects"] == before["projects"] == 0
    assert client.app.state.repository.jobs() == []
