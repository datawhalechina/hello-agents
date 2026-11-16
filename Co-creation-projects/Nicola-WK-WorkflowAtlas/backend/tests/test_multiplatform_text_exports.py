"""Synthetic CSV/TXT/HTML exports use actual public preflight and commit APIs."""
import csv
from datetime import datetime, timedelta, timezone
import io
import json

import pytest

from test_platform_export_compatibility import (
    commit_and_repeat,
    forbid_import_network_and_analysis,
    raw_preview,
)


def wechat_csv(*, content="周三开始联调，文档保留\n第二行含逗号,和引号\"。", local_id="31", server_id="918273645091827364", talker="synthetic@chatroom", time="2026-11-12 09:00:00"):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["localId", "MsgSvrID", "CreateTime", "StrContent", "Type", "NickName", "StrTalker", "IsSender"])
    writer.writeheader()
    writer.writerow({"localId": local_id, "MsgSvrID": server_id, "CreateTime": time, "StrContent": content,
                     "Type": "1", "NickName": "虚构同事", "StrTalker": talker, "IsSender": "0"})
    return stream.getvalue()


@pytest.mark.parametrize("format", ["auto", "csv"])
def test_wechatmsg_csv_quotes_multiline_and_metadata(client, format):
    content = "周三开始联调，文档保留\n第二行含逗号,和引号\"。"
    preview = commit_and_repeat(client, wechat_csv(content=content), format=format)
    message = preview["messages"][0]
    assert message["source_type"] == "wechat"
    assert message["chat_id"] == "synthetic@chatroom" and message["sender"] == "虚构同事"
    assert message["text"] == content
    raw = message["metadata"]["raw"]
    assert raw["StrContent"] == content and raw["IsSender"] == "0" and raw["Type"] == "1"
    assert raw["MsgSvrID"] == "918273645091827364"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-32", "gb18030"])
def test_csv_supported_file_encodings_are_decoded_without_losing_text(client, encoding):
    content = "虚构团队的中文内容，开发时间已确认"
    preview = commit_and_repeat(client, wechat_csv(content=content).encode(encoding))
    assert preview["messages"][0]["text"] == content


@pytest.mark.parametrize("zone,offset", [("UTC", "+00:00"), ("UTC+08:00", "+08:00")])
def test_csv_naive_datetime_obeys_explicit_timezone(client, zone, offset):
    preview = commit_and_repeat(client, wechat_csv(), zone=zone)
    assert preview["messages"][0]["timestamp"].replace("Z", "+00:00").endswith(offset)


def test_wechat_csv_xml_link_body_is_retained_as_original_text(client):
    body = '<msg><appmsg><title>接口验收</title><url>https://example.invalid/synthetic</url></appmsg></msg>'
    preview = commit_and_repeat(client, wechat_csv(content=body))
    assert preview["messages"][0]["text"] == body
    assert preview["messages"][0]["metadata"]["raw"]["StrContent"] == body


def test_wechat_csv_native_local_id_is_conversation_scoped(client):
    from test_platform_export_compatibility import commit_preview
    first, body, options = raw_preview(client, wechat_csv(server_id="", local_id="1", talker="chat-A"))
    assert first["valid"] == 1 and first["issues"] == []
    commit_preview(client, first, body, options)
    second, body2, options2 = raw_preview(client, wechat_csv(server_id="", local_id="1", talker="chat-B"))
    assert second["valid"] == 1 and second["issues"] == [] and second["imported_candidates"] == 1
    assert second["messages"][0]["id"] != first["messages"][0]["id"]
    commit_preview(client, second, body2, options2)
    assert len(client.get("/api/messages").json()) == 2


@pytest.mark.parametrize("server_key", ["MsgSvrID", "msgSvrId"])
def test_wechat_csv_distinct_native_and_local_ids_and_equivalent_timestamps_are_valid(client, server_key):
    epoch = int(datetime(2026, 11, 12, 9, tzinfo=timezone(timedelta(hours=8))).timestamp())
    row = {"localId": "37", server_key: "923456789012345678", "CreateTime": str(epoch), "StrTime": "2026-11-12 09:00:00",
           "StrContent": "同一记录保留服务端和本地标识", "Type": "1", "NickName": "虚构作者", "StrTalker": "synthetic@chatroom"}
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    preview = commit_and_repeat(client, stream.getvalue())
    message = preview["messages"][0]
    assert message["metadata"]["raw"] == row
    assert datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00")).timestamp() == epoch


@pytest.mark.parametrize("format", ["auto", "txt"])
def test_qq_txt_timestamp_nickname_account_and_multiline_body(client, format):
    text = "2026-11-12 09:00:00 虚构同事(12345678)\n接口计划周三联调\n附件说明保留下一行\n2026-11-12 09:05:00 虚构负责人(87654321)\n收到，按计划推进\n"
    preview = commit_and_repeat(client, text, format=format, expected=2)
    first, second = preview["messages"]
    assert first["text"] == "接口计划周三联调\n附件说明保留下一行"
    assert second["text"] == "收到，按计划推进"
    assert first["source_type"] == "qq"
    assert first["sender"] in {"虚构同事", "12345678", "虚构同事(12345678)"}
    assert "12345678" in json.dumps(first["metadata"], ensure_ascii=False)
    assert preview["warnings"]


def test_wechat_style_inline_sender_timestamp_text_export(client):
    text = "2026-11-12 09:00:00 虚构同事: 接口文档已整理\n2026-11-12 09:01:00 虚构负责人: 明天开始评审"
    preview = commit_and_repeat(client, text, expected=2)
    assert [message["text"] for message in preview["messages"]] == ["接口文档已整理", "明天开始评审"]
    assert all(message["source_type"] in {"wechat", "chat"} for message in preview["messages"])


def test_named_sender_before_datetime_export(client):
    text = "虚构同事 2026-11-12 09:00:00\n接口文档已整理\n虚构负责人 2026-11-12 09:01:00\n明天开始评审"
    preview = commit_and_repeat(client, text, expected=2)
    assert preview["messages"][0]["sender"] == "虚构同事"
    assert preview["messages"][0]["text"] == "接口文档已整理"


def test_format_omission_auto_detects_txt_for_preview_commit_and_strict_file(client):
    text = "2026-11-12 09:00:00 虚构同事(12345678)\n接口文档已整理"
    options = {"source_id": "synthetic-auto-default"}
    checked = client.post("/api/import/preview", params=options, content=text.encode())
    assert checked.status_code == 200, checked.text
    preview = checked.json()
    assert preview["format_detected"] == "txt" and preview["valid"] == 1 and preview["issues"] == []
    committed = client.post("/api/import/commit", params={**options, "fingerprint": preview["fingerprint"]}, content=text.encode())
    assert committed.status_code == 200 and committed.json()["imported"] == 1 and committed.json()["warnings"]
    strict = client.post("/api/import/file", params=options, content=text.encode())
    assert strict.status_code == 200 and strict.json()["imported"] == 0 and strict.json()["duplicates"] == 1
    assert strict.json()["warnings"]


def test_identical_txt_occurrences_have_distinct_stable_derived_identities(client):
    text = "2026-11-12 09:00:00 虚构同事(12345678)\n收到\n" * 3
    preview = commit_and_repeat(client, text, expected=3)
    assert len({message["id"] for message in preview["messages"]}) == 3
    assert [message["text"] for message in preview["messages"]] == ["收到"] * 3


def test_generic_html_table_maps_columns_and_preserves_link_metadata(client):
    html = '<html><body><table><tr><th>id</th><th>时间</th><th>发送人</th><th>正文</th><th>chat_id</th></tr><tr><td>html-1</td><td>2026-11-12 09:00:00</td><td>虚构同事</td><td>接口说明<a href="https://example.invalid/brief">需求链接</a></td><td>html-chat</td></tr></table></body></html>'
    preview = commit_and_repeat(client, html)
    message = preview["messages"][0]
    assert "接口说明" in message["text"] and "需求链接" in message["text"]
    assert message["chat_id"] == "html-chat"
    assert "https://example.invalid/brief" in json.dumps(message["metadata"], ensure_ascii=False)


def test_html_message_data_attributes_import_without_network_or_script_execution(client):
    html = '<html><script>throw new Error("SYNTHETIC_UNTRUSTED_SCRIPT")</script><div class="message" data-id="html-msg-1" data-time="2026-11-12 09:00:00" data-sender="虚构同事" data-content="接口开发安排在周三"></div></html>'
    preview = commit_and_repeat(client, html)
    assert preview["messages"][0]["text"] == "接口开发安排在周三"


def test_html_embedded_json_export_uses_recognizable_messages(client):
    row = {"id": "html-json", "time": "2026-11-12 09:00:00", "chat": "oc_synthetic", "sender": "虚构同事", "content": "原始嵌入消息"}
    html = '<html><script type="application/json">' + json.dumps([row], ensure_ascii=False) + '</script></html>'
    preview = commit_and_repeat(client, html)
    assert preview["messages"][0]["text"] == row["content"]


@pytest.mark.parametrize("content,format", [
    ("name,unrelated\n某人,某内容", "csv"),
    ("虚构同事说：开始开发，但没有日期时间", "txt"),
    ("<html><body>开始开发但没有消息记录字段</body></html>", "html"),
])
def test_unrecognized_text_formats_produce_diagnostics_without_invented_messages(client, content, format):
    preview, _, _ = raw_preview(client, content, format=format)
    assert preview["valid"] == 0 and preview["messages"] == [] and preview["issues"]
    assert client.get("/api/messages").json() == []
