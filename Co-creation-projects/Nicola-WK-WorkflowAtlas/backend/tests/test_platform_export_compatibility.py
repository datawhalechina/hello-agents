"""Synthetic cross-platform exports exercise the public import path."""
import json

import pytest


@pytest.fixture(autouse=True)
def forbid_import_network_and_analysis(monkeypatch):
    import socket
    from app.services.processing import ProcessingService
    from app.extraction import direct, holistic

    def forbidden(*args, **kwargs):
        raise AssertionError("Import must remain read-only until confirmation and must never call a model or network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(ProcessingService, "run", forbidden)
    monkeypatch.setattr(direct.DirectAnalyzer, "analyze", forbidden)
    monkeypatch.setattr(holistic.HolisticAnalyzer, "analyze", forbidden)


def raw_preview(client, content, source_id="synthetic-platform", format="auto", zone="UTC+08:00"):
    body = content.encode("utf-8") if isinstance(content, str) else content
    options = {"source_id": source_id, "format": format, "naive_timezone": zone}
    repository = client.app.state.repository
    with repository.lock:
        before = repository.connection.total_changes
    response = client.post("/api/import/preview", params=options, content=body)
    assert response.status_code == 200, response.text
    assert repository.connection.total_changes == before
    return response.json(), body, options


def commit_preview(client, preview, body, options):
    response = client.post("/api/import/commit", params={**options, "fingerprint": preview["fingerprint"]}, content=body)
    assert response.status_code == 200, response.text
    return response.json()


def commit_and_repeat(client, content, source_id="synthetic-platform", format="auto", expected=1, zone="UTC+08:00"):
    from app.connectors.local import parse_messages
    from app.services.import_preflight import decode_import

    preview, body, options = raw_preview(client, content, source_id, format, zone)
    assert preview["issues"] == [], preview["issues"]
    assert preview["total"] == preview["valid"] == expected
    strict = parse_messages(decode_import(body), source_id, format, zone)
    assert [message.model_dump(mode="json") for message in strict] == preview["messages"]
    assert commit_preview(client, preview, body, options)["imported"] == expected
    repeated, _, _ = raw_preview(client, body, source_id, format, zone)
    assert repeated["imported_candidates"] == 0 and repeated["duplicates"] == expected
    assert commit_preview(client, repeated, body, options)["imported"] == 0
    assert len(client.get("/api/messages", params={"source_id": source_id}).json()) == expected
    return preview


def chatlab(platform="wechat", group="synthetic-group", *, native_id="synthetic-native", content="接口验收安排在周三，附件随后补充", type=0):
    message = {"sender": "synthetic-user", "accountName": "虚构同事", "timestamp": 1794445200, "type": type, "content": content}
    if native_id is not None:
        message["platformMessageId"] = native_id
    return {"chatlab": {"version": "0.0.2", "exportedAt": 1794448800},
            "meta": {"name": "虚构团队", "platform": platform, "type": "group", "groupId": group},
            "members": [{"platformId": "synthetic-user", "accountName": "虚构同事", "groupNickname": "虚构昵称"}],
            "messages": [message]}


def stored_contexts(client, source_id="synthetic-platform"):
    repository = client.app.state.repository
    with repository.lock:
        rows = repository.connection.execute("SELECT payload FROM state WHERE key LIKE 'import_context:%'").fetchall()
    return [value for row in rows if (value := json.loads(row[0]))["source_id"] == source_id]


def test_activity_export_fields_import_through_preflight_and_raw_commit(client):
    record = {
        "time": "2026-10-20 08:50:00",
        "kind": "收到或所在会话可见",
        "source": "消息",
        "id": "om_synthetic_activity",
        "chat": "oc_synthetic_activity",
        "sender": "虚构提醒助手",
        "content": '<card title="测试提醒">保留卡片原文</card>',
        "link": "https://applink.feishu.cn/client/chat/open?openChatId=oc_synthetic_activity",
        "attachments": [],
    }
    content = json.dumps([record], ensure_ascii=False).encode("utf-8")
    options = {"source_id": "synthetic-platform", "format": "json", "naive_timezone": "UTC+08:00"}
    checked = client.post("/api/import/preview", params=options, content=content)
    assert checked.status_code == 200
    preview = checked.json()
    assert preview["total"] == preview["valid"] == 1, preview["issues"]
    assert preview["issues"] == []
    committed = client.post("/api/import/commit", params={**options, "fingerprint": preview["fingerprint"]}, content=content)
    assert committed.status_code == 200 and committed.json()["imported"] == 1
    message = client.app.state.repository.evidence("synthetic-platform", record["id"])
    assert message.text == record["content"]
    assert message.chat_id == record["chat"]
    assert message.timestamp.isoformat() == "2026-10-20T08:50:00+08:00"
    assert message.metadata["raw"] == record


@pytest.mark.parametrize("format", ["auto", "json", "jsonl"])
def test_legacy_feishu_shape_remains_compatible_and_keeps_scalar_prose(client, format):
    record = {"message_id": "om_synthetic_legacy", "chat_id": "oc_synthetic", "sender": {"id": "ou_synthetic"},
              "create_time": "2026-11-12 09:00:00", "msg_type": "text", "content": "0"}
    preview = commit_and_repeat(client, json.dumps([record] if format != "jsonl" else record), format=format)
    message = preview["messages"][0]
    assert message["id"] == record["message_id"] and message["text"] == "0"
    assert message["source_type"] == "feishu" and message["metadata"]["raw"] == record


@pytest.mark.parametrize("platform", ["wechat", "qq"])
def test_chatlab_official_envelope_preserves_conversation_sender_and_raw_fields(client, platform):
    envelope = chatlab(platform)
    preview = commit_and_repeat(client, json.dumps(envelope, ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == platform and message["chat_id"] == "synthetic-group"
    assert message["text"] == envelope["messages"][0]["content"]
    assert message["sender"] in {"synthetic-user", "虚构同事", "虚构昵称"}
    assert "synthetic-native" in json.dumps(message["metadata"], ensure_ascii=False)
    for key, value in envelope["messages"][0].items():
        assert message["metadata"]["raw"][key] == value
    contexts = stored_contexts(client)
    assert len(contexts) == 1
    assert contexts[0]["context"]["meta"] == envelope["meta"]
    assert contexts[0]["context"]["members"] == envelope["members"]
    assert message["metadata"]["import"]["source_context_hash"] == contexts[0]["context_hash"]


def test_chatlab_native_identity_is_scoped_to_conversation_without_losing_original(client):
    first, second = chatlab(group="group-A"), chatlab(group="group-B")
    first_preview, body, options = raw_preview(client, json.dumps(first))
    assert first_preview["valid"] == 1, first_preview["issues"]
    commit_preview(client, first_preview, body, options)
    second_preview, body2, options2 = raw_preview(client, json.dumps(second))
    assert second_preview["valid"] == 1 and second_preview["issues"] == []
    assert second_preview["imported_candidates"] == 1
    assert second_preview["messages"][0]["id"] != first_preview["messages"][0]["id"]
    commit_preview(client, second_preview, body2, options2)
    stored = client.get("/api/messages").json()
    assert {message["chat_id"] for message in stored} == {"group-A", "group-B"}
    assert len(stored) == 2
    assert all("synthetic-native" in json.dumps(message["metadata"]) for message in stored)


@pytest.mark.parametrize("type,content", [(1, None), (4, None), (7, '<card title="需求确认">https://example.invalid/brief</card>')])
def test_chatlab_attachments_and_cards_preserve_available_evidence(client, type, content):
    envelope = chatlab(type=type, content=content)
    envelope["messages"][0]["attachment"] = {"name": "synthetic.pdf", "url": "https://example.invalid/synthetic.pdf"}
    preview = commit_and_repeat(client, json.dumps(envelope, ensure_ascii=False))
    message = preview["messages"][0]
    assert message["text"].strip()
    if content is not None:
        assert message["text"] == content
    assert message["metadata"]["raw"]["content"] == content
    assert message["metadata"]["raw"]["attachment"] == envelope["messages"][0]["attachment"]


def test_chatlab_official_jsonl_header_member_and_message_records(client):
    envelope = chatlab(native_id=None)
    lines = [{"_type": "header", "chatlab": envelope["chatlab"], "meta": envelope["meta"]},
             {"_type": "member", **envelope["members"][0]}, {"_type": "message", **envelope["messages"][0]}]
    preview = commit_and_repeat(client, "\n".join(json.dumps(row, ensure_ascii=False) for row in lines), format="jsonl")
    assert preview["format_detected"] == "jsonl" and preview["warnings"]
    assert preview["messages"][0]["source_type"] == "wechat"


def test_recognized_export_without_native_ids_preserves_identical_occurrences(client):
    envelope = chatlab(native_id=None)
    envelope["messages"] *= 3
    preview = commit_and_repeat(client, json.dumps(envelope, ensure_ascii=False), expected=3)
    assert len({message["id"] for message in preview["messages"]}) == 3
    assert preview["warnings"]
    assert len({message["text"] for message in preview["messages"]}) == 1


def test_common_qq_json_keeps_numeric_id_and_zero_sender(client):
    row = {"message_id": 0, "time": "2026-11-12 09:00:00", "group_id": "synthetic-qq", "sender": 0,
           "message": "任务将在10点开始，请保留数字标识"}
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == "qq" and message["chat_id"] == "synthetic-qq"
    assert message["sender"] == "0" and message["text"] == row["message"]
    assert message["metadata"]["raw"] == row


def test_common_qq_nested_sender_identity_and_observed_name_are_preserved(client):
    row = {"message_id": 918273645, "time": 1794445200, "group_id": "synthetic-qq", "sender": {"user_id": 12345678, "nickname": "虚构QQ同事"},
           "message": "接口开始开发"}
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["sender"] == "虚构QQ同事"
    assert message["metadata"]["raw"]["sender"] == row["sender"]
    assert "12345678" in json.dumps(message["metadata"])


def test_canonical_platform_attachment_kind_reaches_source_statistics(client):
    envelope = chatlab(type=1, content=None)
    preview = commit_and_repeat(client, json.dumps(envelope, ensure_ascii=False))
    message = preview["messages"][0]
    assert message["metadata"]["import"]["message_kind"] == "image"
    response = client.get("/api/sources/analysis", params={"source_id": "synthetic-platform"})
    assert response.status_code == 200
    assert response.json()["message_types"] == {"image": 1}
    assert response.json()["attachment_messages"] == 1 and response.json()["textual_messages"] == 0


def test_strict_file_import_returns_derived_identity_warning(client):
    envelope = chatlab(native_id=None)
    response = client.post("/api/import/file", params={"source_id": "synthetic-platform", "format": "auto"},
                           content=json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
    assert response.status_code == 200 and response.json()["imported"] == 1
    assert response.json()["warnings"]


@pytest.mark.parametrize("row,platform", [
    ({"MsgSvrID": "918273645", "CreateTime": "2026-11-12 09:00:00", "StrTalker": "wx-synthetic-chat", "message_type": 1,
      "StrContent": "微信原生字段的接口开发安排", "NickName": "虚构同事"}, "wechat"),
    ({"message_type": "group", "group_id": "qq-synthetic-chat", "message_id": 101, "time": "2026-11-12 09:00:00",
      "sender": {"user_id": 12345678, "nickname": "虚构同事"}, "message": "QQ原生字段的接口开发安排"}, "qq"),
])
def test_native_platform_fields_take_precedence_over_feishu_message_type_alias(client, row, platform):
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == platform
    assert message["text"] == row.get("StrContent", row.get("message"))
    assert message["metadata"]["raw"] == row
    assert message["metadata"]["import"]["message_kind"] == "text"


@pytest.mark.parametrize("zone,offset", [("UTC", "+00:00"), ("UTC+08:00", "+08:00")])
def test_generic_activity_naive_time_uses_only_chosen_timezone(client, zone, offset):
    record = {"id": "activity-time", "time": "2026-11-12 09:00:00", "chat": "oc_synthetic", "sender": "虚构作者", "content": "保留时间"}
    preview = commit_and_repeat(client, json.dumps([record], ensure_ascii=False), zone=zone)
    assert preview["messages"][0]["timestamp"].replace("Z", "+00:00").endswith(offset)
    assert preview["messages"][0]["metadata"]["raw"]["time"] == record["time"]


def test_explicit_offset_survives_platform_and_selected_timezone(client):
    row = {"id": "explicit-offset", "time": "2026-11-12T09:00:00-04:00", "chat": "oc_synthetic", "sender": "虚构作者", "content": "保留时区"}
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False), zone="UTC+08:00")
    assert preview["messages"][0]["timestamp"].endswith("-04:00")
