import json
import unittest
from urllib.parse import parse_qs, urlparse

from app.connectors.feishu import (
    FeishuHistoryClient, FeishuReadError, HttpResponse,
    SyncCheckpoint, incremental_checkpoint,
)
from app.connectors.local import ImportValidationError, parse_messages


def raw(message_id="om_1", text="任务完成", stamp="1700000000123"):
    return {
        "message_id": message_id, "msg_type": "text", "create_time": stamp,
        "sender": {"id": "ou_1", "name": "工程师"},
        "body": {"content": json.dumps({"text": text}, ensure_ascii=False)},
    }


def response(items, more=False, token=None):
    return HttpResponse(200, {"code": 0, "data": {"items": items, "has_more": more, "page_token": token}})


class LocalTests(unittest.TestCase):
    def test_feishu_raw_and_cli_envelopes(self):
        records = [raw()]
        for body in ({"code": 0, "data": {"items": records}}, {"ok": True, "data": {"messages": records}}):
            item = parse_messages(json.dumps(body), "source")[0]
            self.assertEqual(item.text, "任务完成")
            self.assertEqual(item.sender, "工程师")
            self.assertEqual(item.metadata["raw"], records[0])
            self.assertIsNotNone(item.timestamp.tzinfo)

    def test_jsonl_and_standards(self):
        body = {"id": "1", "source_id": "s", "text": "原始证据", "timestamp": "2026-11-01T12:00:00+08:00"}
        result = parse_messages(json.dumps(body) + "\n\n" + json.dumps({**body, "id": "2"}), "s", "jsonl")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].timestamp.utcoffset().total_seconds(), 28800)

    def test_rejects_bad_identity_naive_time_and_partial_jsonl(self):
        body = {"id": "1", "source_id": "other", "text": "x", "timestamp": "2026-11-01T12:00:00+08:00"}
        for value in (body, {**body, "source_id": "s", "timestamp": "2026-11-01T12:00:00"}, {"ok": False}):
            with self.assertRaises(ImportValidationError):
                parse_messages(json.dumps(value), "s")
        with self.assertRaisesRegex(ImportValidationError, "line 2"):
            parse_messages(json.dumps(raw()) + "\ninvalid", "s", "jsonl")

    def test_post_resource_and_recalled_content(self):
        post = {**raw(), "msg_type": "post", "body": {"content": json.dumps({"zh_cn": {"title": "需求", "content": [[{"tag": "text", "text": "上线"}, {"tag": "a", "text": "文档", "href": "https://example.invalid"}]]}})}}
        result = parse_messages(json.dumps([post, {**raw("2"), "msg_type": "image"}, {**raw("3"), "deleted": True}]), "s")
        self.assertEqual(result[0].text, "需求\n上线文档")
        self.assertEqual(result[1].text, "[image message]")
        self.assertEqual(result[2].text, "[recalled message]")


class FeishuTests(unittest.TestCase):
    def test_pagination_retry_final_token_and_checkpoint(self):
        requests, sleeps, commits = [], [], []
        replies = iter([HttpResponse(429, {}, {"Retry-After": "0"}), response([raw(), raw()], True, "next"), response([raw("2")], False, "ignored")])
        def transport(url, headers):
            requests.append((url, headers))
            return next(replies)
        client = FeishuHistoryClient("test-token", transport=transport, sleeper=sleeps.append)
        original = SyncCheckpoint("source", "oc_chat", start_time=1699999990, end_time=1700000020)
        final = client.sync(original, lambda messages, state: commits.append((messages, state)))
        self.assertTrue(final.complete)
        self.assertIsNone(final.page_token)
        self.assertFalse(original.complete)
        self.assertEqual(len(commits[0][0]), 1)
        self.assertEqual(len(commits), 2)
        self.assertEqual(parse_qs(urlparse(requests[-1][0]).query)["page_token"], ["next"])
        self.assertEqual(requests[0][1]["Authorization"], "Bearer test-token")
        next_run = incremental_checkpoint(final, end_time=1700000100)
        self.assertEqual(next_run.start_time, 1699999998)
        self.assertFalse(next_run.complete)
        self.assertIsNone(next_run.page_token)
        self.assertEqual(SyncCheckpoint.from_dict(final.to_dict()), final)

    def test_sink_failure_never_acknowledges_page(self):
        original = SyncCheckpoint("s", "oc_c")
        client = FeishuHistoryClient("test", transport=lambda *_: response([raw()], True, "n"), sleeper=lambda _: None)
        def failed_commit(*_):
            raise RuntimeError("disk full")
        with self.assertRaisesRegex(RuntimeError, "disk full"):
            client.sync(original, failed_commit)
        self.assertIsNone(original.page_token)
        self.assertEqual(original.high_watermark_ms, 0)

    def test_invalid_page_and_cursor_do_not_commit(self):
        for reply in (response([{"message_id": "broken"}]), response([raw()], True, None), response([{**raw(), "chat_id": "wrong"}])):
            client = FeishuHistoryClient("test", transport=lambda *_, r=reply: r, sleeper=lambda _: None)
            commits = []
            with self.assertRaises(FeishuReadError):
                client.sync(SyncCheckpoint("s", "oc_c"), lambda *args: commits.append(args))
            self.assertEqual(commits, [])

    def test_retry_budget_and_host_boundary(self):
        calls = []
        def unavailable(*_):
            calls.append(1)
            return HttpResponse(503, {})
        client = FeishuHistoryClient("test", transport=unavailable, sleeper=lambda _: None, max_attempts=3)
        with self.assertRaises(FeishuReadError):
            client.fetch_page(SyncCheckpoint("s", "oc_c"))
        self.assertEqual(len(calls), 3)
        with self.assertRaises(ValueError):
            FeishuHistoryClient("test", base_url="https://attacker.invalid")
        with self.assertRaises(ValueError):
            incremental_checkpoint(SyncCheckpoint("s", "oc_c"))


if __name__ == "__main__":
    unittest.main()
