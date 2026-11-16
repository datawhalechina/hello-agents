"""Adapter-specific safety and bounded metadata checks."""

import hashlib
import json
import unittest

from app.connectors.formats import source_contexts
from app.connectors.local import ImportValidationError, parse_messages
from app.connectors.preview import preview_messages
from app.connectors.context import reply_references


class MultiplatformTests(unittest.TestCase):
    def test_native_wechat_message_type_does_not_select_feishu_adapter(self):
        raw = {
            "MsgSvrID": "native-wechat",
            "CreateTime": 1700000000,
            "StrTalker": "conversation",
            "message_type": 1,
            "StrContent": "微信原始正文",
        }
        message = parse_messages(json.dumps([raw]), "s")[0]
        self.assertEqual(message.source_type, "wechat")
        self.assertEqual(message.text, raw["StrContent"])
        self.assertEqual(message.metadata["import"]["message_kind"], "text")
        self.assertEqual(message.metadata["raw"], raw)

    def test_qq_group_event_string_message_is_text_not_attachment(self):
        raw = {
            "message_type": "group",
            "group_id": 123,
            "message_id": 1,
            "time": 1700000000,
            "sender": {"nickname": "测试人"},
            "message": "QQ原始正文",
        }
        message = parse_messages(json.dumps([raw]), "s")[0]
        self.assertEqual(message.source_type, "qq")
        self.assertEqual(message.text, raw["message"])
        self.assertEqual(message.metadata["import"]["message_kind"], "text")
        self.assertEqual(message.metadata["raw"], raw)

    def test_generic_multiconversation_containers_keep_separate_native_ids(self):
        for container in ("chats", "conversations", "sessions"):
            payload = {
                container: [
                    {
                        "id": chat,
                        "name": "合成会话",
                        "messages": [
                            {"id": 1, "time": 1703001600, "sender": "测试人", "content": "原文"}
                        ],
                    }
                    for chat in ("first", "second")
                ]
            }
            messages = parse_messages(json.dumps(payload), "s")
            self.assertEqual({message.chat_id for message in messages}, {"first", "second"})
            self.assertEqual(len({message.id for message in messages}), 2)
            self.assertEqual(len(source_contexts(json.dumps(payload))), 2)

    def test_single_session_envelope_preserves_context_and_requires_real_time(self):
        payload = {
            "session": {"id": "chat", "name": "合成会话", "platform": "wechat"},
            "messages": [{"id": 1, "time": 1703001600, "sender": "测试人", "content": "原文"}],
        }
        result = preview_messages(json.dumps(payload), "s")
        self.assertEqual(result.valid, 1)
        self.assertEqual(result.messages[0].chat_id, "chat")
        self.assertEqual(result.messages[0].source_type, "wechat")
        del payload["messages"][0]["time"]
        result = preview_messages(json.dumps(payload), "s")
        self.assertEqual(result.valid, 0)
        self.assertTrue(any(issue.code == "missing_timestamp" for issue in result.issues))

    def test_standard_arbitrary_metadata_and_export_metadata_remain_original(self):
        standard = {
            "id": "m",
            "source_id": "s",
            "text": "标准原文",
            "timestamp": "2026-11-12T09:00:00+08:00",
            "metadata": {"import": 123},
        }
        message = parse_messages(json.dumps([standard]), "s")[0]
        self.assertEqual(message.metadata, standard["metadata"])
        exported = {
            "platformMessageId": "wx-message",
            "CreateTime": 1703001600,
            "StrContent": "原生原文",
            "StrTalker": "wx-conversation",
            "metadata": {"arbitrary": [1, 2]},
        }
        message = parse_messages(json.dumps([exported]), "s")[0]
        self.assertEqual(message.source_type, "wechat")
        self.assertEqual(message.metadata["raw"], exported)

    def test_onebot_segments_use_message_id_and_preserve_original_chain(self):
        chain = [
            {"type": "text", "data": {"text": "第一段"}},
            {
                "type": "image",
                "data": {"url": "https://example.invalid/image", "file": "image.png"},
            },
            {"type": "text", "data": {"text": "末段"}},
        ]
        raw = {
            "id": "event-unique",
            "message_id": 1,
            "self": {"platform": "qq", "user_id": "account"},
            "type": "message",
            "detail_type": "group",
            "group_id": "chat",
            "time": 1703001600.2,
            "sender": {"user_id": 0, "nickname": "合成人员"},
            "message": chain,
        }
        reply = {
            **raw,
            "message_id": 2,
            "message": [
                {"type": "reply", "data": {"id": 1}},
                {"type": "text", "data": {"text": "回复原文"}},
            ],
        }
        messages = parse_messages(json.dumps([raw, reply]), "s")
        self.assertEqual(messages[0].text, "第一段[image message]末段")
        self.assertEqual(messages[0].metadata["raw"], raw)
        self.assertEqual(messages[0].metadata["import"]["native_id"], "1")
        self.assertEqual(messages[0].metadata["import"]["message_kind"], "post")
        self.assertEqual(reply_references(messages[1]), [messages[0].id])

    def test_onebot_conversation_namespaces_include_account_and_chat_type(self):
        base = {
            "message_id": 1,
            "time": 1703001600,
            "sender": {"user_id": 5, "nickname": "测试人"},
            "message": [{"type": "record", "data": {"file": "audio.silk"}}],
        }
        rows = [
            {**base, "message_type": "group", "group_id": 100, "self_id": 1},
            {**base, "message_type": "private", "user_id": 100, "self_id": 1},
            {**base, "message_type": "private", "user_id": 100, "self_id": 2},
        ]
        messages = parse_messages(json.dumps(rows), "s")
        self.assertEqual(len({item.id for item in messages}), 3)
        self.assertTrue(
            all(item.metadata["import"]["message_kind"] == "audio" for item in messages)
        )

    def test_onebot_malformed_segments_are_record_errors(self):
        for segment in (
            {"type": "text", "data": {"text": None}},
            {"type": "reply", "data": {}},
            {"type": "image"},
            "wrong",
        ):
            raw = {"message_id": 1, "time": 1703001600, "group_id": 1, "message": [segment]}
            result = preview_messages(json.dumps(raw), "s")
            self.assertEqual(result.valid, 0)
            self.assertEqual(result.issues[0].code, "invalid_content")

    def test_large_member_context_is_stored_once_and_hashes_match(self):
        body = {
            "chatlab": {"version": "0.0.2", "exportedAt": 1703001600},
            "meta": {
                "name": "合成规模验证",
                "platform": "qq",
                "type": "group",
                "groupId": "test-group",
            },
            "members": [
                {
                    "platformId": str(index),
                    "accountName": f"合成人员{index}",
                    "avatar": "data:image/png;base64," + "a" * 1000,
                }
                for index in range(500)
            ],
            "messages": [
                {
                    "platformMessageId": f"message-{index}",
                    "sender": "0",
                    "timestamp": 1703001600 + index,
                    "type": 0,
                    "content": "合成消息",
                }
                for index in range(100)
            ],
        }
        content = json.dumps(body, ensure_ascii=False)
        preview = preview_messages(content, "size-check", "auto")
        self.assertEqual(preview.valid, 100)
        serialized = json.dumps(
            [item.model_dump(mode="json") for item in preview.messages], ensure_ascii=False
        )
        self.assertLess(len(serialized), len(content))
        contexts = source_contexts(content, "auto")
        self.assertEqual(len(contexts), 1)
        digest, context = next(iter(contexts.items()))
        self.assertEqual(context["members"], body["members"])
        self.assertNotIn("messages", context)
        self.assertEqual(
            digest,
            hashlib.sha256(
                json.dumps(
                    context, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode()
            ).hexdigest(),
        )
        self.assertTrue(
            all(
                item.metadata["import"]["source_context_hash"] == digest
                for item in preview.messages
            )
        )
        self.assertTrue(
            all(
                "avatar" not in item.metadata["import"]["sender_members"][0]
                for item in preview.messages
            )
        )

    def test_legacy_feishu_source_id_and_timestamp_keep_output(self):
        raw = {
            "message_id": "om_legacy",
            "source_id": "s",
            "timestamp": "2026-11-12T09:00:00+08:00",
            "sender": {"name": "测试人"},
            "content": "原始内容",
        }
        message = parse_messages(json.dumps([raw]), "s")[0]
        self.assertEqual(message.id, "om_legacy")
        self.assertEqual(message.source_type, "feishu")
        self.assertEqual(message.metadata, {"raw": raw})

    def test_server_and_local_ids_keep_separate_meanings_and_bound_namespace(self):
        raw = {
            "MsgSvrID": "server",
            "localId": 9,
            "StrTalker": "conversation" * 100,
            "CreateTime": 1703001600,
            "NickName": "测试人",
            "Type": 1,
            "StrContent": "原始文本",
        }
        message = parse_messages(json.dumps([raw]), "s")[0]
        self.assertEqual(message.metadata["import"]["native_id"], "server")
        self.assertEqual(message.metadata["raw"]["localId"], 9)
        self.assertLessEqual(len(message.id), 300)
        self.assertEqual(message.metadata["import"]["message_kind"], "text")

    def test_nested_sender_and_zero_native_id(self):
        raw = {
            "message_id": 0,
            "time": 1703001600,
            "sender": {"user_id": 0, "nickname": "零号"},
            "group_id": "g",
            "message": "null",
        }
        message = parse_messages(json.dumps([raw]), "s")[0]
        self.assertEqual(message.sender, "零号")
        self.assertEqual(message.metadata["import"]["sender_id"], "0")
        self.assertEqual(message.metadata["import"]["native_id"], "0")
        self.assertEqual(message.text, "null")

    def test_html_preserves_link_image_and_ignores_executable_text(self):
        content = '<div class="message" data-time="2026-11-12 09:00:00" data-sender="测试人"><div class="content">正文<a href="https://example.invalid">链接</a><img src="private.png" title="原图"><script>business_fact_fake()</script></div></div>'
        result = preview_messages(content, "s", "html")
        self.assertEqual(result.valid, 1)
        self.assertEqual(result.messages[0].text, "正文链接")
        self.assertEqual(result.messages[0].metadata["import"]["source_html"], content)

    def test_alias_conflicts_and_invalid_formats_remain_explicit(self):
        raw = {
            "id": "m",
            "time": "2026-11-12T09:00:00+08:00",
            "timestamp": "2026-11-13T09:00:00+08:00",
            "sender": "测试人",
            "content": "原文",
        }
        preview = preview_messages(json.dumps(raw), "s")
        self.assertEqual(preview.valid, 0)
        self.assertEqual(preview.issues[0].code, "ambiguous_fields")
        for content in (
            '{"messages":[BROKEN',
            "<html><body>没有消息结构</body></html>",
            "没有时间和发送人的任意文本",
        ):
            with self.assertRaises(ImportValidationError):
                parse_messages(content, "s", "auto")

    def test_non_json_formats_enforce_record_and_html_depth_limits(self):
        content = "time,sender,content\n" + "2026-11-12 09:00:00,测试人,消息\n" * 10001
        with self.assertRaisesRegex(ImportValidationError, "10000"):
            preview_messages(content, "s", "csv")
        nested = "<div>" * 300 + "text" + "</div>" * 300
        preview = preview_messages(nested, "s", "html")
        self.assertEqual(preview.valid, 0)
        self.assertEqual(preview.issues[0].code, "invalid_html")


if __name__ == "__main__":
    unittest.main()
