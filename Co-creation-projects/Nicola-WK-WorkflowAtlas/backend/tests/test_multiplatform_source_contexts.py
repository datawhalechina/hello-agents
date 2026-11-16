"""Import root context is retained once with atomic writes and scoped deletion."""
from copy import deepcopy
import json
import sqlite3

import pytest

from test_platform_export_compatibility import (
    chatlab,
    commit_preview,
    forbid_import_network_and_analysis,
    raw_preview,
    stored_contexts,
)


def test_full_chatlab_header_and_members_are_stored_once_with_compact_message_references(client):
    envelope = chatlab()
    avatar = "data:image/png;base64," + "SYNTHETIC_AVATAR" * 400
    envelope["meta"]["groupAvatar"] = avatar
    envelope["members"][0]["avatar"] = avatar
    envelope["members"] += [{"platformId": f"other-{number}", "accountName": f"虚构其他成员{number}", "avatar": avatar} for number in range(40)]
    original = envelope["messages"][0]
    envelope["messages"] = [{**original, "platformMessageId": f"native-{number}", "content": f"虚构工作观察{number}"} for number in range(40)]
    preview, body, options = raw_preview(client, json.dumps(envelope, ensure_ascii=False))
    assert preview["valid"] == 40 and preview["issues"] == []
    assert stored_contexts(client) == []
    for message in preview["messages"]:
        encoded = json.dumps(message["metadata"], ensure_ascii=False)
        assert avatar not in encoded
        assert "虚构其他成员39" not in encoded
        assert message["metadata"]["import"]["source_context_hash"]
    assert commit_preview(client, preview, body, options)["imported"] == 40
    contexts = stored_contexts(client)
    assert len(contexts) == 1
    context = contexts[0]["context"]
    assert context["chatlab"] == envelope["chatlab"]
    assert context["meta"] == envelope["meta"]
    assert context["members"] == envelope["members"]
    assert {message["metadata"]["import"]["source_context_hash"] for message in preview["messages"]} == {contexts[0]["context_hash"]}
    repeated, _, _ = raw_preview(client, body)
    assert repeated["duplicates"] == 40 and repeated["imported_candidates"] == 0
    assert commit_preview(client, repeated, body, options)["imported"] == 0
    assert len(stored_contexts(client)) == 1


def test_new_export_header_and_unrelated_members_do_not_turn_identical_message_into_conflict(client):
    first = chatlab()
    first_preview, body, options = raw_preview(client, json.dumps(first, ensure_ascii=False))
    assert first_preview["valid"] == 1 and first_preview["issues"] == []
    commit_preview(client, first_preview, body, options)
    original_message = client.get("/api/messages").json()[0]
    second = deepcopy(first)
    second["chatlab"]["exportedAt"] += 3600
    second["members"].append({"platformId": "unrelated-new-member", "accountName": "虚构新增成员"})
    second_preview, second_body, second_options = raw_preview(client, json.dumps(second, ensure_ascii=False))
    assert second_preview["valid"] == 1 and second_preview["issues"] == []
    assert second_preview["duplicates"] == 1 and second_preview["imported_candidates"] == 0
    report = commit_preview(client, second_preview, second_body, second_options)
    assert report["imported"] == 0 and report["duplicates"] == 1
    assert client.get("/api/messages").json() == [original_message]
    contexts = stored_contexts(client)
    assert len(contexts) == 2
    assert {item["context"]["chatlab"]["exportedAt"] for item in contexts} == {first["chatlab"]["exportedAt"], second["chatlab"]["exportedAt"]}


@pytest.mark.parametrize("endpoint", ["file", "commit"])
def test_source_context_storage_failure_rolls_back_imported_messages(client, endpoint):
    preview, body, options = raw_preview(client, json.dumps(chatlab(), ensure_ascii=False))
    assert preview["valid"] == 1 and preview["issues"] == []
    repository = client.app.state.repository
    with repository.connection:
        repository.connection.execute("CREATE TRIGGER reject_import_context BEFORE INSERT ON state WHEN NEW.key LIKE 'import_context:%' BEGIN SELECT RAISE(ABORT, 'synthetic source-context failure'); END")
    params = {**options, "fingerprint": preview["fingerprint"]} if endpoint == "commit" else options
    with pytest.raises(sqlite3.IntegrityError):
        client.post(f"/api/import/{endpoint}", params=params, content=body)
    assert repository.messages() == [] and stored_contexts(client) == []


def test_source_delete_removes_its_root_contexts_and_keeps_prefix_related_source(client):
    sources = ("synthetic-platform", "synthetic-platform:retained")
    for source in sources:
        preview, body, options = raw_preview(client, json.dumps(chatlab(), ensure_ascii=False), source_id=source)
        commit_preview(client, preview, body, options)
        assert len(stored_contexts(client, source)) == 1
    preview_response = client.get("/api/sources/delete-preview", params={"source_id": sources[0]})
    assert preview_response.status_code == 200
    deletion = preview_response.json()
    response = client.request("DELETE", "/api/sources", params={"source_id": sources[0]}, json={"confirmation": sources[0], "expected_messages": deletion["messages"], "expected_version": deletion["version"]})
    assert response.status_code == 200, response.text
    assert stored_contexts(client, sources[0]) == []
    assert len(stored_contexts(client, sources[1])) == 1
    remaining = client.get("/api/messages").json()
    assert len(remaining) == 1 and remaining[0]["source_id"] == sources[1]
