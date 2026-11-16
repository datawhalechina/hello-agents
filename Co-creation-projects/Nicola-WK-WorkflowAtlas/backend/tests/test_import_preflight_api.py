"""Import previews use synthetic uploads, remain read-only and never run models."""
import json

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app

SOURCE = "预检/虚构来源"
PRIVATE = "SYNTHETIC-RAW-ONLY-DO-NOT-LOG"


@pytest.fixture(autouse=True)
def prohibit_analysis(monkeypatch):
    from app.agents import orchestrator
    from app.extraction import direct, holistic, remote
    from app.services.processing import ProcessingService

    def forbidden(*args, **kwargs):
        raise AssertionError("Import preflight must not invoke analysis or any real model")

    monkeypatch.setattr(ProcessingService, "run", forbidden)
    monkeypatch.setattr(direct, "DirectAnalyzer", forbidden)
    monkeypatch.setattr(holistic, "HolisticAnalyzer", forbidden)
    monkeypatch.setattr(remote, "RemoteReasoner", forbidden)
    monkeypatch.setattr(orchestrator, "RemoteReasoner", forbidden)


def standard(identifier="m1", **overrides):
    return {"id": identifier, "source_id": SOURCE, "text": "虚构上传记录", "sender": "虚构作者", "timestamp": "2026-01-01T09:00:00+08:00", **overrides}


def raw(identifier="raw1", **overrides):
    return {"message_id": identifier, "msg_type": "text", "sender": "虚构作者", "content": "虚构原始消息", "create_time": "2026-01-01T09:00:00", **overrides}


def preview(client, content, *, format="json", naive_timezone="UTC+08:00", headers=None):
    body = content.encode("utf-8") if isinstance(content, str) else content
    return client.post("/api/import/preview", params={"source_id": SOURCE, "format": format, "naive_timezone": naive_timezone}, content=body, headers=headers or {"Content-Type": "text/plain"})


def preview_rows(client, records, **kwargs):
    response = preview(client, json.dumps(records, ensure_ascii=False), **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def seed(client, records):
    response = client.post("/api/import", json={"source_id": SOURCE, "messages": records})
    assert response.status_code == 200, response.text


def database_snapshot(client):
    repository = client.app.state.repository
    with repository.lock:
        tables = [row[0] for row in repository.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return repository.connection.total_changes, {table: sorted(tuple(row) for row in repository.connection.execute('SELECT * FROM "' + table + '"')) for table in tables}


def test_mixed_issues_are_all_reported_read_only_and_explicit_subset_import_works(client, caplog):
    seed(client, [standard("existing")])
    records = [standard("good"), raw("bad-time", create_time=PRIVATE), raw("", content=PRIVATE), raw("bad-body", content="")]
    before = database_snapshot(client)
    data = preview_rows(client, records)
    assert database_snapshot(client) == before
    assert data["total"] == 4 and data["valid"] == 1 and data["imported_candidates"] == 1 and data["duplicates"] == 0
    assert [message["id"] for message in data["messages"]] == ["good"]
    assert {issue["position"] for issue in data["issues"]} == {2, 3, 4}
    for issue in data["issues"]:
        assert issue["field"] and issue["code"] and issue["detail"]
        assert issue["raw"] == records[issue["position"] - 1]
        assert PRIVATE not in issue["detail"]
    assert PRIVATE not in caplog.text
    assert "candidate_positions" not in data and "candidate_lines" not in data and "candidate_raw" not in data
    # This explicit separate request is the only operation that stores candidates.
    imported = client.post("/api/import", json={"source_id": SOURCE, "messages": data["messages"]})
    assert imported.status_code == 200 and imported.json()["imported"] == 1
    assert {message["id"] for message in client.get("/api/messages").json()} == {"good", "existing"}


@pytest.mark.parametrize("existing", [False, True])
def test_exact_duplicate_rows_have_one_representative_and_precise_counts(client, existing):
    row = standard("same")
    if existing:
        seed(client, [row])
    before = database_snapshot(client)
    data = preview_rows(client, [row, row, row])
    assert data["total"] == 3 and data["valid"] == 1 and len(data["messages"]) == 1
    assert data["duplicates"] == (3 if existing else 2)
    assert data["imported_candidates"] == (0 if existing else 1) and data["issues"] == []
    assert database_snapshot(client) == before


def test_batch_conflicting_identity_excludes_every_version_with_original_positions(client):
    original = standard("conflict", text=PRIVATE + " original")
    changed = standard("conflict", text=PRIVATE + " changed")
    records = [original, standard("safe"), original, changed]
    before = database_snapshot(client)
    data = preview_rows(client, records)
    assert database_snapshot(client) == before
    assert data["valid"] == 1 and data["imported_candidates"] == 1
    assert [message["id"] for message in data["messages"]] == ["safe"]
    conflicts = [issue for issue in data["issues"] if issue["code"] == "immutable_conflict"]
    assert {issue["position"] for issue in conflicts} == {1, 3, 4}
    assert all(issue["field"] == "id" and PRIVATE not in issue["detail"] for issue in conflicts)


def test_database_conflict_excludes_group_without_overwriting_existing_record(client):
    original = standard("existing", text="原始不可变正文")
    seed(client, [original])
    before = database_snapshot(client)
    data = preview_rows(client, [standard("safe"), {**original, "text": PRIVATE}, original])
    assert database_snapshot(client) == before
    assert [message["id"] for message in data["messages"]] == ["safe"]
    conflicts = [issue for issue in data["issues"] if issue["code"] == "immutable_conflict"]
    assert {issue["position"] for issue in conflicts} == {2, 3}
    assert all(issue["field"] == "id" for issue in conflicts)
    assert client.get("/api/messages").json()[0]["text"] == original["text"]


def test_database_change_after_preview_causes_atomic_commit_conflict(client):
    data = preview_rows(client, [standard("fresh"), standard("racing")])
    assert data["issues"] == [] and data["imported_candidates"] == 2
    seed(client, [standard("racing", text="预检之后另一操作已写入的原文")])
    before = database_snapshot(client)
    response = client.post("/api/import", json={"source_id": SOURCE, "messages": data["messages"]})
    assert response.status_code == 409
    # SQLite may count attempted, rolled-back writes; logical contents stay intact.
    assert database_snapshot(client)[1] == before[1]
    assert [message["id"] for message in client.get("/api/messages").json()] == ["racing"]


def test_jsonl_auto_detection_recovers_all_valid_lines_and_preserves_physical_lines(client):
    content = "\ufeff\n" + json.dumps(standard("first"), ensure_ascii=False) + "\n\n{" + PRIVATE + "\n" + json.dumps(standard("second"), ensure_ascii=False) + "\n"
    before = database_snapshot(client)
    response = preview(client, content, format="json")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["format_detected"] == "jsonl" and data["total"] == 3 and data["valid"] == 2
    assert {message["id"] for message in data["messages"]} == {"first", "second"}
    assert len(data["issues"]) >= 1 and {issue["line"] for issue in data["issues"]} == {4}
    assert {issue["position"] for issue in data["issues"]} == {2}
    assert any(PRIVATE in str(issue["raw"]) for issue in data["issues"])
    assert all(PRIVATE not in issue["detail"] for issue in data["issues"])
    assert database_snapshot(client) == before


def test_jsonl_reports_every_syntax_type_and_field_error_without_hiding_later_rows(client):
    lines = [json.dumps(standard("first")), "", '{"broken":', json.dumps(PRIVATE),
             json.dumps(raw("bad-time", create_time=PRIVATE)), json.dumps(standard("last"))]
    before = database_snapshot(client)
    response = preview(client, "\n".join(lines), format="jsonl")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 5 and data["valid"] == 2
    assert {message["id"] for message in data["messages"]} == {"first", "last"}
    assert {issue["position"] for issue in data["issues"]} == {2, 3, 4}
    assert {issue["line"] for issue in data["issues"]} == {3, 4, 5}
    assert all(PRIVATE not in issue["detail"] for issue in data["issues"])
    assert database_snapshot(client) == before


def test_preview_detects_conflicting_identity_at_original_jsonl_lines(client):
    first = standard("same", text="初次正文")
    second = standard("same", text="改写正文")
    content = "\n" + json.dumps(first) + "\n\n" + json.dumps(standard("safe")) + "\n" + json.dumps(second)
    response = preview(client, content, format="jsonl")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 3 and data["valid"] == 1 and data["messages"][0]["id"] == "safe"
    conflicts = [issue for issue in data["issues"] if issue["code"] == "immutable_conflict"]
    assert {issue["position"] for issue in conflicts} == {1, 3}
    assert {issue["line"] for issue in conflicts} == {2, 5}
    assert client.get("/api/messages").json() == []


def test_standard_records_never_receive_guessed_ids_or_timezones(client):
    missing_id = raw()
    missing_id.pop("message_id")
    missing_time = raw("no-time")
    missing_time.pop("create_time")
    data = preview_rows(client, [standard("valid"), standard("naive", timestamp="2026-01-01T09:00:00"), missing_id, missing_time])
    assert data["total"] == 4 and data["valid"] == 1
    assert [message["id"] for message in data["messages"]] == ["valid"]
    assert {issue["position"] for issue in data["issues"]} == {2, 3, 4}
    assert client.get("/api/messages").json() == []


@pytest.mark.parametrize("zone, expected", [("UTC", "+00:00"), ("UTC+08:00", "+08:00")])
def test_only_raw_naive_timestamps_use_explicit_selected_timezone(client, zone, expected):
    records = [raw(), standard("explicit", timestamp="2026-01-01T09:00:00-05:00")]
    data = preview_rows(client, records, naive_timezone=zone)
    assert data["issues"] == [] and data["valid"] == 2
    messages = {message["id"]: message for message in data["messages"]}
    assert messages["raw1"]["timestamp"].endswith(expected) or (zone == "UTC" and messages["raw1"]["timestamp"].endswith("Z"))
    assert messages["explicit"]["timestamp"].endswith("-05:00")
    assert messages["raw1"]["metadata"]["raw"] == records[0]


def test_malformed_document_returns_issue_without_fabricated_records(client):
    before = database_snapshot(client)
    response = preview(client, '[{"id":"' + PRIVATE)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["messages"] == [] and data["valid"] == 0 and data["imported_candidates"] == 0 and data["issues"]
    assert all(PRIVATE not in issue["detail"] for issue in data["issues"])
    assert database_snapshot(client) == before


def test_strict_file_import_still_rejects_entire_mixed_file(client):
    content = json.dumps([standard("good"), raw("bad", create_time=PRIVATE)], ensure_ascii=False).encode()
    before = database_snapshot(client)
    response = client.post("/api/import/file", params={"source_id": SOURCE, "format": "json"}, content=content)
    assert response.status_code == 400 and PRIVATE not in response.text
    assert database_snapshot(client)[1] == before[1]


def test_preview_authentication_does_not_expose_uploaded_raw_records(tmp_path):
    settings = Settings(database_path=str(tmp_path / "auth.db"), api_token="synthetic-auth", _env_file=None)
    with TestClient(create_app(settings)) as secured:
        body = json.dumps([raw("bad", create_time=PRIVATE)])
        for headers in ({}, {"Authorization": "Bearer wrong-synthetic-token"}):
            denied = preview(secured, body, headers=headers)
            assert denied.status_code == 401 and PRIVATE not in denied.text
        allowed = preview(secured, body, headers={"Authorization": "Bearer synthetic-auth"})
        assert allowed.status_code == 200 and PRIVATE in json.dumps(allowed.json()["issues"][0]["raw"])
        assert PRIVATE not in allowed.json()["issues"][0]["detail"]


def test_oversized_preview_is_rejected_before_parse_without_mutation(tmp_path):
    settings = Settings(database_path=str(tmp_path / "small.db"), max_body_bytes=128, _env_file=None)
    with TestClient(create_app(settings)) as small:
        before = database_snapshot(small)
        response = preview(small, json.dumps([standard(text=PRIVATE * 20)]))
        assert response.status_code == 413 and PRIVATE not in response.text
        assert database_snapshot(small) == before


def test_invalid_utf8_is_a_safe_client_error_and_never_stored(client, caplog):
    body = PRIVATE.encode() + b"\xff\xfe"
    before = database_snapshot(client)
    response = preview(client, body)
    assert response.status_code == 400 and PRIVATE not in response.text
    assert PRIVATE not in caplog.text and database_snapshot(client) == before


def commit_raw(client, content, fingerprint, *, source=SOURCE, format="json", naive_timezone="UTC+08:00", headers=None):
    params = {"source_id": source, "format": format, "naive_timezone": naive_timezone}
    if fingerprint is not None:
        params["fingerprint"] = fingerprint
    return client.post("/api/import/commit", params=params, content=content.encode("utf-8") if isinstance(content, str) else content,
                       headers=headers or {"Content-Type": "application/octet-stream"})


def checked_raw(client, records, **kwargs):
    content = json.dumps(records, ensure_ascii=False).encode("utf-8")
    response = preview(client, content, **kwargs)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["fingerprint"]) == 64 and set(data["fingerprint"]) <= set("0123456789abcdef")
    return content, data


def test_raw_commit_replays_confirmed_full_file_without_preview_writes(client):
    before = database_snapshot(client)
    content, data = checked_raw(client, [raw("first"), raw("second")])
    assert database_snapshot(client) == before and data["valid"] == 2 and not data["issues"]
    response = commit_raw(client, content, data["fingerprint"])
    assert response.status_code == 200 and response.json()["imported"] == 2 and response.json()["duplicates"] == 0
    assert client.get("/api/messages").json() == data["messages"]


def test_raw_commit_explicit_partial_candidates_skips_errors_with_visible_warning(client):
    content, data = checked_raw(client, [raw("valid"), raw("bad", create_time=PRIVATE), raw("valid")])
    assert data["valid"] == 1 and data["duplicates"] == 1 and data["issues"]
    assert client.get("/api/messages").json() == []
    response = commit_raw(client, content, data["fingerprint"])
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1 and response.json()["duplicates"] == 0
    assert response.json()["warnings"] and PRIVATE not in response.text
    assert [message["id"] for message in client.get("/api/messages").json()] == ["valid"]


@pytest.mark.parametrize("fingerprint", [None, "short", "g" * 64])
def test_raw_commit_requires_well_formed_fingerprint_without_writing(client, fingerprint):
    before = database_snapshot(client)
    response = commit_raw(client, json.dumps([raw()]), fingerprint)
    assert response.status_code == 422 and database_snapshot(client) == before


def test_wrong_valid_shape_fingerprint_rejects_commit_without_writing(client):
    content, data = checked_raw(client, [raw()])
    wrong = ("1" if data["fingerprint"][0] == "0" else "0") + data["fingerprint"][1:]
    before = database_snapshot(client)
    response = commit_raw(client, content, wrong)
    assert response.status_code == 409 and database_snapshot(client) == before


@pytest.mark.parametrize("change", ["content", "timezone", "format", "source"])
def test_raw_commit_rejects_file_or_option_change_since_preview(client, change):
    content, data = checked_raw(client, [raw()])
    kwargs = {}
    if change == "content":
        content = json.dumps([raw(content="已经改变的虚构正文")]).encode()
    elif change == "timezone":
        kwargs["naive_timezone"] = "UTC"
    elif change == "format":
        kwargs["format"] = "jsonl"
    else:
        kwargs["source"] = SOURCE + "/changed"
    before = database_snapshot(client)
    response = commit_raw(client, content, data["fingerprint"], **kwargs)
    assert response.status_code == 409 and database_snapshot(client) == before


def test_raw_commit_database_conflict_after_preview_rejects_entire_candidate_set(client):
    content, data = checked_raw(client, [standard("fresh"), standard("racing")])
    seed(client, [standard("racing", text="另一操作写入的不可变正文")])
    before = database_snapshot(client)
    response = commit_raw(client, content, data["fingerprint"])
    assert response.status_code == 409 and database_snapshot(client) == before
    assert [message["id"] for message in client.get("/api/messages").json()] == ["racing"]


def test_raw_commit_empty_candidate_set_is_not_reported_as_success(client):
    content, data = checked_raw(client, [raw("bad", create_time=PRIVATE)])
    assert data["valid"] == 0 and data["issues"]
    before = database_snapshot(client)
    response = commit_raw(client, content, data["fingerprint"])
    assert response.status_code == 400 and PRIVATE not in response.text
    assert database_snapshot(client) == before


def test_raw_commit_handles_normalized_metadata_expansion_beyond_request_limit(tmp_path):
    settings = Settings(database_path=str(tmp_path / "expansion.db"), max_body_bytes=3000, _env_file=None)
    with TestClient(create_app(settings)) as small:
        original = raw(content="Synthetic long text. " * 90)
        before = database_snapshot(small)
        content, data = checked_raw(small, [original])
        normalized_body = json.dumps({"source_id": SOURCE, "messages": data["messages"]}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        assert len(content) <= settings.max_body_bytes < len(normalized_body)
        # This is the former UI failure: normalized JSON duplicates metadata.raw.
        normalized = small.post("/api/import", content=normalized_body, headers={"Content-Type": "application/json"})
        assert normalized.status_code == 413 and database_snapshot(small) == before
        committed = commit_raw(small, content, data["fingerprint"])
        assert committed.status_code == 200 and committed.json()["imported"] == 1
        saved = small.get("/api/messages").json()[0]
        assert saved["text"] == original["content"] and saved["metadata"]["raw"] == original


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_original_bom_encoded_bytes_preview_and_commit_without_loss(client, encoding):
    records = [raw(content="虚构中文与emoji🙂原始正文")]
    content = json.dumps(records, ensure_ascii=False).encode(encoding)
    before = database_snapshot(client)
    response = preview(client, content)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["valid"] == 1 and not data["issues"] and database_snapshot(client) == before
    committed = commit_raw(client, content, data["fingerprint"])
    assert committed.status_code == 200 and committed.json()["imported"] == 1
    saved = client.get("/api/messages").json()[0]
    assert saved["text"] == records[0]["content"] and saved["metadata"]["raw"] == records[0]


def test_raw_commit_requires_bearer_even_with_correct_fingerprint(tmp_path):
    settings = Settings(database_path=str(tmp_path / "commit-auth.db"), api_token="synthetic-auth", _env_file=None)
    with TestClient(create_app(settings)) as secured:
        auth = {"Authorization": "Bearer synthetic-auth"}
        content, data = checked_raw(secured, [raw()], headers=auth)
        before = database_snapshot(secured)
        denied = commit_raw(secured, content, data["fingerprint"])
        assert denied.status_code == 401 and database_snapshot(secured) == before
        committed = commit_raw(secured, content, data["fingerprint"], headers=auth)
        assert committed.status_code == 200 and committed.json()["imported"] == 1
