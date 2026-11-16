"""Synthetic regression coverage for immutable evidence context projections."""
from copy import deepcopy
import unittest

from app.connectors.context import (
    build_identity_map, iter_text_segments, message_segments,
    reply_references, resolve_sender_name,
)
from app.schemas import StandardMessage


def message(message_id="m1", source_id="synthetic-source", sender="ou_synthetic", raw=None, text="合成任务"):
    return StandardMessage(id=message_id, source_id=source_id, sender=sender, text=text,
                           timestamp="2026-11-09T09:00:00+08:00", metadata={"raw": raw or {}})


class ReplyContextTests(unittest.TestCase):
    def test_parent_root_and_thread_are_ordered_deduplicated_and_self_excluded(self):
        item = message(raw={"parent_id": "p1", "root_id": "p1", "thread_id": "m1"})
        item.thread_id = "thread1"
        before = item.model_dump(mode="json")
        self.assertEqual(reply_references(item), ["p1", "thread1"])
        self.assertEqual(item.model_dump(mode="json"), before)

    def test_malformed_metadata_does_not_create_a_reply(self):
        item = message(raw={"parent_id": {"id": "p1"}, "root_id": " ", "thread_id": 12})
        self.assertEqual(reply_references(item), [])


class IdentityContextTests(unittest.TestCase):
    def test_identity_is_source_scoped_and_any_conflict_is_excluded(self):
        rows = [
            message(raw={"mentions": [{"id": "ou_a", "name": "合成人员甲"}]}),
            message(message_id="m2", raw={"mentions": [{"id": "ou_a", "name": "合成人员乙"}]}),
            message(message_id="m3", source_id="other-source", raw={"mentions": [{"id": "ou_a", "name": "合成人员丙"}]}),
        ]
        identities = build_identity_map(rows)
        self.assertNotIn(("synthetic-source", "ou_a"), identities)
        self.assertEqual(identities[("other-source", "ou_a")], "合成人员丙")

    def test_sender_and_mention_names_resolve_without_mutation(self):
        rows = [message(raw={"sender": {"id": "ou_synthetic"}, "mentions": [{"id": "ou_synthetic", "name": "合成人员甲"}]})]
        before = deepcopy(rows[0].model_dump())
        self.assertEqual(resolve_sender_name(rows[0], build_identity_map(rows)), "合成人员甲")
        self.assertEqual(rows[0].model_dump(), before)

    def test_opaque_sender_is_retained_when_name_missing(self):
        item = message(raw={"sender": {"id": "ou_synthetic"}})
        self.assertEqual(resolve_sender_name(item, {}), "ou_synthetic")

    def test_explicit_sender_name_is_a_supported_identity_observation(self):
        item = message(sender="合成人员甲", raw={"sender": {"id": "ou_synthetic", "name": "合成人员甲"}})
        self.assertEqual(build_identity_map([item]), {("synthetic-source", "ou_synthetic"): "合成人员甲"})
        self.assertEqual(resolve_sender_name(item, build_identity_map([item])), "合成人员甲")

    def test_invalid_mentions_are_ignored(self):
        item = message(raw={"mentions": [None, "invalid", {"id": "x", "name": " "}, {"id": {"bad": 1}, "name": "甲"}]})
        self.assertEqual(build_identity_map([item]), {})


class TextSegmentTests(unittest.TestCase):
    def test_html_blocks_split_but_each_quote_and_offset_is_exact(self):
        text = "<p>甲项目</p><p>完成 <b>接口</b> &amp; 测试</p><p>安排验收<br>提交记录</p>"
        segments = message_segments(text)
        self.assertEqual([s.quote for s in segments], ["甲项目", "完成 <b>接口</b> &amp; 测试", "安排验收", "提交记录"])
        self.assertEqual(segments[1].display_text, "完成 接口 & 测试")
        self.assertTrue(all(text[s.start:s.end] == s.quote for s in segments))
        self.assertEqual(iter_text_segments(text), [s.quote for s in segments])

    def test_newlines_trim_literal_whitespace_without_changing_content(self):
        text = "  任务甲\r\n\n\t任务乙  \n任务丙\u00a0"
        segments = message_segments(text)
        self.assertEqual([s.quote for s in segments], ["任务甲", "任务乙", "任务丙"])
        self.assertTrue(all(text[s.start:s.end] == s.quote for s in segments))

    def test_incomplete_markup_and_links_are_never_executed_or_fetched(self):
        text = '<p>安排接口<a href="https://example.invalid/private">文档</a><p>继续验收'
        segments = message_segments(text)
        self.assertEqual([s.display_text for s in segments], ["安排接口文档", "继续验收"])
        self.assertIn('href="https://example.invalid/private"', segments[0].quote)

    def test_entities_are_decoded_only_for_display(self):
        text = "<p>&lt;合成项目&gt; &nbsp; 准备</p>"
        segment = message_segments(text)[0]
        self.assertEqual(segment.quote, "&lt;合成项目&gt; &nbsp; 准备")
        self.assertEqual(segment.display_text, "<合成项目> 准备")

    def test_empty_text_produces_no_segments(self):
        self.assertEqual(message_segments("\n<p> </p><br>"), [])

    def test_script_style_and_comment_markup_never_become_visible_facts(self):
        text = '<p>准备接口</p><script><p>伪造任务完成</p></script><!-- <p>伪造交付</p> --><style>.任务{color:red}</style><p>安排验收</p>'
        self.assertEqual(iter_text_segments(text), ["准备接口", "安排验收"])

    def test_repeated_paragraphs_have_distinct_literal_offsets(self):
        text = "<p>合成任务</p><p>合成任务</p>"
        segments = message_segments(text)
        self.assertEqual(len(segments), 2)
        self.assertNotEqual(segments[0].start, segments[1].start)
        self.assertTrue(all(text[s.start:s.end] == s.quote for s in segments))


if __name__ == "__main__":
    unittest.main()
