import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import AppError, Settings
from src.services import parse_object, TavilySearch
from src.workflow import MAX_ROUNDS, Store, Workflow
from tests.support import BRIEF, ModelDouble, SearchDouble


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "projects.sqlite3"
        self.store = Store(self.path)
        self.model, self.search = ModelDouble(), SearchDouble()
        self.flow = Workflow(self.store, self.model, self.search)
        self.state = self.flow.create("我希望自己管理任务，第一版不做支付。")

    def confirmed(self):
        self.flow.confirm(self.state, copy.deepcopy(BRIEF))
        return self.state

    def test_interview_passes_history_and_saves_updated_brief(self):
        self.flow.interview(self.state)
        self.flow.add_answer(self.state, "主要在工作时添加")
        self.flow.interview(self.state)
        self.assertEqual(self.model.calls[-1][1]["conversation"][-1]["content"], "主要在工作时添加")
        self.assertEqual(self.store.get(self.state["id"])["round"], 2)

    def test_answer_cannot_be_added_twice_before_processing(self):
        with self.assertRaises(AppError):
            self.flow.add_answer(self.state, "重复回答")

    def test_round_cap_moves_to_confirmation(self):
        self.state["round"] = MAX_ROUNDS - 1
        self.flow.interview(self.state)
        self.assertTrue(self.state["ready"])
        self.assertEqual(self.state["question"], "")
        with self.assertRaises(AppError):
            self.flow.interview(self.state)

    def test_confirmation_is_required_for_generation(self):
        with self.assertRaises(AppError):
            self.flow.generate(self.state, False)
        self.assertFalse(self.model.calls)

    def test_confirmed_snapshot_is_independent(self):
        self.confirmed()
        self.state["brief"]["exclusions"] = "手动改动草稿"
        self.assertEqual(self.state["confirmed_brief"]["exclusions"], "不做支付")

    def test_generation_keeps_confirmed_requirements_and_cites_sources(self):
        self.confirmed()
        self.flow.generate(self.state, True)
        self.assertEqual([r for r, _ in self.model.calls], ["research", "assess", "writer", "audit"])
        self.assertIn("不做支付", self.state["report"])
        self.assertIn("https://example.com/test-only", self.state["report"])
        self.assertIn("验收条件：", self.state["report"])
        for _, context in self.model.calls:
            self.assertEqual(context["confirmed_brief"], BRIEF)

    def test_unknown_citation_removed(self):
        self.confirmed()
        self.model.invalid_source = True
        self.flow.generate(self.state, True)
        self.assertEqual(self.state["competitors"], [])
        self.assertTrue(any("移除" in n for n in self.state["notices"]))
        self.assertNotIn("S99", self.state["report"])

    def test_failed_search_does_not_invent_competitors(self):
        self.confirmed()
        self.search.fail = True
        self.flow.generate(self.state, True)
        self.assertEqual(self.state["competitors"], [])
        self.assertNotIn("research", [r for r, _ in self.model.calls])
        self.assertIn("搜索失败", self.state["report"])

    def test_skipping_search_is_explicit(self):
        self.confirmed()
        self.flow.generate(self.state, False)
        self.assertFalse(self.search.calls)
        self.assertIn("未进行联网", self.state["report"])

    def test_conflicts_are_reported_without_changing_confirmation(self):
        self.confirmed()
        self.model.conflicts = ["测试冲突：与用户排除支付的要求矛盾"]
        self.flow.generate(self.state, False)
        self.assertIn("需要优先修正的需求冲突", self.state["report"])
        self.assertEqual(self.state["confirmed_brief"], BRIEF)

    def test_reopening_invalidates_all_derived_results(self):
        self.confirmed()
        self.flow.generate(self.state, True)
        self.flow.reopen(self.state)
        self.assertIsNone(self.state["confirmed_brief"])
        for key in ("report", "sources", "competitors", "conflicts"):
            self.assertFalse(self.state[key])
        self.assertIsNone(self.state["prd"])

    def test_model_failure_keeps_answer_for_retry(self):
        original = copy.deepcopy(self.state["messages"])
        self.model.fail = "interview"
        with self.assertRaises(AppError):
            self.flow.interview(self.state)
        self.assertEqual(self.state["messages"], original)
        self.model.fail = None
        self.flow.interview(self.state)
        self.assertEqual(sum(m["role"] == "user" for m in self.state["messages"]), 1)

    def test_restart_recovers_busy_projects(self):
        self.state["busy"] = True
        self.store.save(self.state)
        restored = Store(self.path).get(self.state["id"])
        self.assertFalse(restored["busy"])
        self.assertIn("中断", restored["error"])

    def test_missing_required_confirmation_fields_rejected(self):
        with self.assertRaises(AppError):
            self.flow.confirm(self.state, {"title": "只有名字"})

    def test_empty_prd_rejected(self):
        self.confirmed()
        original = self.model.run
        self.model.run = lambda role, ctx: {"requirements": []} if role == "writer" else original(role, ctx)
        with self.assertRaises(AppError):
            self.flow.generate(self.state, False)
        self.assertEqual(self.state["report"], "")


class BoundaryTests(unittest.TestCase):
    def test_json_fence_is_supported_but_bad_payload_rejected(self):
        self.assertEqual(parse_object('```json\n{"ready":true}\n```'), {"ready": True})
        for payload in ("[]", "null", "报告：{}", '{"broken"'):
            with self.subTest(payload=payload), self.assertRaises(AppError):
                parse_object(payload)

    def test_settings_do_not_reveal_secrets(self):
        cfg = Settings(model="test", api_key="test-secret-value", search_key="test-search-secret")
        self.assertNotIn("test-secret-value", str(cfg.public()))
        self.assertNotIn("test-search-secret", repr(cfg))

    def test_invalid_service_address_rejected(self):
        for address in ("file:///tmp/key", "https://user:password@example.com/v1", "missing-host"):
            with self.subTest(address=address), self.assertRaises(AppError):
                Settings(model="test", api_key="test-key", base_url=address).validate()

    def test_search_key_required(self):
        with self.assertRaises(AppError):
            TavilySearch("").search("query")

    def test_search_filters_unsafe_urls_and_duplicates(self):
        import io, json
        payload = {"results": [{"url": "javascript:alert(1)", "title": "bad"},
                    {"url": "https://example.com", "title": "test", "content": "text"},
                    {"url": "https://example.com", "title": "duplicate"}]}
        with patch("src.services.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = TavilySearch("test-key").search("query")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "S1")


if __name__ == "__main__":
    unittest.main()
