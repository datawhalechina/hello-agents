"""Public OneBot 11 event/segment structures with synthetic QQ content."""
import json

import pytest

from test_platform_export_compatibility import (
    commit_and_repeat,
    commit_preview,
    forbid_import_network_and_analysis,
    raw_preview,
)


def event(message=None, *, native_id=101, private=False, **changes):
    row = {"time": 1794445200, "self_id": 90000001, "post_type": "message",
           "message_type": "private" if private else "group", "sub_type": "friend" if private else "normal",
           "message_id": native_id, "user_id": 12345678,
           "message": message if message is not None else [{"type": "text", "data": {"text": "接口开发安排在周三"}}],
           "raw_message": "接口开发安排在周三", "font": 0,
           "sender": {"user_id": 12345678, "nickname": "虚构QQ同事", "card": "虚构群名片"}}
    if not private:
        row["group_id"] = 88776655
    return {**row, **changes}


def test_onebot_message_segments_and_raw_cq_are_distinct_preserved_representations(client):
    row = event([
        {"type": "text", "data": {"text": "接口开发"}},
        {"type": "at", "data": {"qq": "12345678"}},
        {"type": "text", "data": {"text": "周三联调"}},
        {"type": "image", "data": {"file": "synthetic-image", "url": "https://example.invalid/synthetic.png"}},
    ], raw_message="接口开发[CQ:at,qq=12345678]周三联调[CQ:image,file=synthetic-image]", id="synthetic-wrapper-event-id")
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == "qq" and message["chat_id"]
    assert "接口开发" in message["text"] and "周三联调" in message["text"]
    assert message["sender"] in {"虚构QQ同事", "虚构群名片"}
    assert str(message["metadata"]["import"]["native_id"]) == "101"
    assert message["metadata"]["raw"] == row
    assert message["metadata"]["raw"]["id"] == "synthetic-wrapper-event-id"


@pytest.mark.parametrize("type,kind", [("image", "image"), ("record", "audio")])
def test_onebot_nontext_segments_have_available_placeholder_and_correct_source_statistics(client, type, kind):
    row = event([{"type": type, "data": {"file": "file:///C:/SYNTHETIC_DO_NOT_OPEN", "url": "https://example.invalid/private"}}], raw_message=f"[CQ:{type},file=SYNTHETIC]")
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["text"].strip() and message["metadata"]["raw"] == row
    assert message["metadata"]["import"]["message_kind"] == kind
    response = client.get("/api/sources/analysis", params={"source_id": "synthetic-platform"})
    assert response.status_code == 200 and response.json()["message_types"] == {kind: 1}
    assert response.json()["attachment_messages"] == 1


def test_onebot_reply_segment_references_normalized_original_message(client):
    original = event(native_id=100)
    reply = event([{"type": "reply", "data": {"id": "100"}}, {"type": "text", "data": {"text": "收到，按这个安排推进"}}], raw_message="[CQ:reply,id=100]收到，按这个安排推进")
    preview = commit_and_repeat(client, json.dumps([original, reply], ensure_ascii=False), expected=2)
    first, second = preview["messages"]
    assert second["thread_id"] == first["id"]
    assert second["metadata"]["raw"]["message"][0]["data"]["id"] == "100"
    assert "收到，按这个安排推进" in second["text"]


@pytest.mark.parametrize("type,data", [
    ("xml", {"data": '<msg><title>接口说明</title><script>SYNTHETIC_SCRIPT</script></msg>'}),
    ("json", {"data": '{"title":"接口说明","url":"https://example.invalid/synthetic"}'}),
])
def test_onebot_xml_json_segments_preserve_original_data_without_execution(client, type, data):
    row = event([{"type": type, "data": data}], raw_message=f"[CQ:{type},data=SYNTHETIC]")
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    assert preview["messages"][0]["text"].strip()
    assert preview["messages"][0]["metadata"]["raw"]["message"] == row["message"]


def test_onebot_private_events_use_peer_identity_and_retained_sender_fields(client):
    row = event(private=True, user_id=0, sender={"user_id": 0, "nickname": "虚构私聊同事"})
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == "qq" and message["chat_id"]
    assert message["sender"] == "虚构私聊同事"
    assert message["metadata"]["raw"]["user_id"] == 0


def test_onebot_private_qq_accounts_do_not_collide_on_equal_peer_and_native_id(client):
    first = event(private=True)
    second = event(private=True, self_id=90000002)
    first_preview, body, options = raw_preview(client, json.dumps([first], ensure_ascii=False))
    assert first_preview["valid"] == 1, first_preview["issues"]
    commit_preview(client, first_preview, body, options)
    second_preview, second_body, second_options = raw_preview(client, json.dumps([second], ensure_ascii=False))
    assert second_preview["valid"] == 1 and second_preview["issues"] == []
    assert second_preview["imported_candidates"] == 1
    assert second_preview["messages"][0]["id"] != first_preview["messages"][0]["id"]
    commit_preview(client, second_preview, second_body, second_options)
    assert len(client.get("/api/messages").json()) == 2


def test_onebot_raw_cq_string_is_available_when_segment_field_is_absent(client):
    literal = "收到[CQ:image,file=file:///C:/SYNTHETIC_DO_NOT_OPEN]"
    row = event(raw_message=literal)
    row.pop("message")
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    assert preview["messages"][0]["text"] == literal
    assert preview["messages"][0]["metadata"]["raw"] == row


def test_onebot_invalid_middle_segment_record_does_not_hide_following_message(client):
    first = event(native_id=1)
    invalid = event([{"type": "text", "data": "INVALID_SEGMENT_OBJECT"}], native_id=2)
    last = event(native_id=3)
    preview, body, options = raw_preview(client, json.dumps([first, invalid, last], ensure_ascii=False))
    assert preview["total"] == 3 and preview["valid"] == 2
    assert {issue["position"] for issue in preview["issues"]} == {2}
    assert commit_preview(client, preview, body, options)["imported"] == 2


@pytest.mark.parametrize("detail_type", ["private", "group"])
def test_onebot12_self_platform_event_identity_and_sender_without_extra_lookup(client, detail_type):
    row = {"id": "synthetic-v12-event-id", "self": {"platform": "qq", "user_id": "90000001"},
           "time": 1794445200.125, "type": "message", "detail_type": detail_type, "sub_type": "",
           "message_id": "native-v12-message", "message": [{"type": "text", "data": {"text": "接口开发安排在周三"}}],
           "alt_message": "接口开发安排在周三", "user_id": "12345678"}
    if detail_type == "group":
        row["group_id"] = "88776655"
    preview = commit_and_repeat(client, json.dumps([row], ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == "qq" and message["chat_id"]
    assert message["sender"] == "12345678" and message["text"] == "接口开发安排在周三"
    assert message["metadata"]["import"]["native_id"] == "native-v12-message"
    assert message["metadata"]["import"]["message_kind"] == "text"
    assert message["metadata"]["raw"] == row
