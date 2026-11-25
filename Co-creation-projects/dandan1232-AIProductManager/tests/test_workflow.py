import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import AppError, Settings
from src.services import parse_object, TavilySearch
from src.workflow import MAX_ROUNDS, Store, Workflow, first_release_requirements
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

    def test_regeneration_failures_keep_saved_report_until_retry_succeeds(self):
        self.confirmed()
        self.model.conflicts = ["上一版的待解决冲突"]
        self.flow.generate(self.state, True)
        old_id = self.state["report_id"]
        self.flow.review_requirement(self.state, 0, "first_release", "上一版的用户验收条件", old_id)
        result_fields = ("report", "report_id", "report_generated_at", "prd", "prd_reviews", "assessment",
                         "sources", "competitors", "research_summary", "conflicts", "notices")
        previous = self.store.get(self.state["id"])
        self.model.conflicts = []

        for stage, role in (("research", "research"), ("assess", "assess"), ("writing", "writer"), ("audit", "audit")):
            with self.subTest(stage=stage):
                self.model.fail = role
                with self.assertRaises(AppError):
                    self.flow.generate(self.state, True)
                saved = self.store.get(self.state["id"])
                self.assertEqual(saved["stage"], stage)
                for key in result_fields:
                    self.assertEqual(saved[key], previous[key], key)
                    self.assertEqual(self.state[key], previous[key], key)

        self.model.fail = None
        with patch.object(self.search, "search", return_value=[]):
            self.flow.generate(self.state, True)
        current = self.store.get(self.state["id"])
        self.assertEqual(current["stage"], "done")
        self.assertNotEqual(current["report_id"], old_id)
        self.assertNotEqual(current["report_generated_at"], previous["report_generated_at"])
        self.assertEqual(current["prd_reviews"], {})
        self.assertEqual(current["conflicts"], [])
        self.assertEqual(current["sources"], [])
        self.assertIn("未获得竞品资料", current["report"])
        self.assertNotIn("上一版的用户验收条件", current["report"])

    def test_interrupted_regeneration_keeps_report_readable_during_run_and_restart(self):
        self.confirmed()
        self.flow.generate(self.state, True)
        old_report = self.state["report"]
        old_prd = copy.deepcopy(self.state["prd"])
        self.state["busy"] = True
        original = self.model.run

        def interrupt_at_audit(role, context):
            if role == "audit":
                running = self.store.get(self.state["id"])
                self.assertTrue(running["busy"])
                self.assertEqual(running["stage"], "audit")
                self.assertFalse(running["online"])
                self.assertEqual(running["report"], old_report)
                self.assertEqual(running["prd"], old_prd)
                self.assertTrue(running["sources"])
                raise KeyboardInterrupt()
            return original(role, context)

        with patch.object(self.model, "run", side_effect=interrupt_at_audit), self.assertRaises(KeyboardInterrupt):
            self.flow.generate(self.state, False)

        restored = Store(self.path).get(self.state["id"])
        self.assertFalse(restored["busy"])
        self.assertIn("中断", restored["error"])
        self.assertEqual(restored["report"], old_report)
        self.assertEqual(restored["prd"], old_prd)
        self.assertTrue(restored["sources"])

    def test_initial_generation_failure_does_not_publish_partial_results(self):
        self.confirmed()
        self.model.fail = "audit"
        with self.assertRaises(AppError):
            self.flow.generate(self.state, True)
        saved = self.store.get(self.state["id"])
        self.assertEqual(saved["stage"], "audit")
        self.assertFalse(saved["report"])
        for key in ("report_id", "prd", "assessment"):
            self.assertIsNone(saved[key])
        self.assertEqual(saved["sources"], [])
        self.assertEqual(saved["competitors"], [])

    def test_acceptance_uses_reviewed_requirements_in_prd_order_for_legacy_report(self):
        self.confirmed()
        original = self.model.run

        def model_reply(role, context):
            result = original(role, context)
            if role == "writer":
                item = result["requirements"][0]
                result["requirements"].extend([{**item, "name": "检索任务"}, {**item, "name": "查看任务"}])
            if role == "acceptance":
                result["cases"].reverse()
                result["cases"][0]["status"] = "passed"
            return result

        with patch.object(self.model, "run", side_effect=model_reply):
            self.flow.generate(self.state, False)
            self.state.pop("report_id")
            self.state.pop("acceptance_suite")
            self.flow.review_requirement(self.state, 2, "first_release", "列表显示同名任务", None)
            self.flow.review_requirement(self.state, 0, "first_release", "保存后返回列表", None)
            report = self.state["report"]
            self.flow.generate_acceptance(self.state)

        requirements = first_release_requirements(self.state)
        self.assertEqual(self.model.calls[-1], ("acceptance", {"requirements": requirements}))
        self.assertEqual([item["id"] for item in requirements], ["F01", "F03"])
        self.assertEqual(self.state["report"], report)
        self.assertEqual(self.state["stage"], "done")
        suite = self.state["acceptance_suite"]
        self.assertIsNone(suite["report_id"])
        self.assertEqual([(case["requirement_id"], case["acceptance"], case["status"]) for case in suite["cases"]],
                         [("F01", "保存后返回列表", "pending"), ("F03", "列表显示同名任务", "pending")])
        self.flow.mark_acceptance(self.state, suite["id"], "F03", "needs_fix")
        self.flow.review_requirement(self.state, 1, "later", "以后增加检索", None)
        self.flow.review_requirement(self.state, 0, "first_release", " 保存后返回列表 ", None)
        self.assertEqual(self.store.get(self.state["id"])["acceptance_suite"]["cases"][1]["status"], "needs_fix")
        self.flow.review_requirement(self.state, 0, "first_release", "保存后可继续编辑", None)
        self.assertIsNone(self.state["acceptance_suite"])
        with self.assertRaises(AppError) as stale:
            self.flow.mark_acceptance(self.state, suite["id"], "F03", "passed")
        self.assertEqual(stale.exception.status, 409)

    def test_acceptance_rejects_missing_wrong_duplicate_and_empty_case_fields(self):
        self.confirmed()
        self.flow.generate(self.state, False)
        with self.assertRaises(AppError) as no_selection:
            self.flow.generate_acceptance(self.state)
        self.assertEqual(no_selection.exception.status, 409)
        self.flow.review_requirement(self.state, 0, "first_release", "任务可见", self.state["report_id"])
        report = self.state["report"]
        case = {"requirement_id": "F01", "steps": ["打开任务列表"], "expected": "任务可见"}
        for cases in ([], [{**case, "requirement_id": "F02"}], [case, case],
                      [{**case, "steps": []}], [{**case, "steps": ["打开列表", " "]}], [{**case, "expected": " "}]):
            with self.subTest(cases=cases), patch.object(self.model, "run", return_value={"cases": cases}):
                with self.assertRaises(AppError) as invalid:
                    self.flow.generate_acceptance(self.state)
                self.assertEqual(invalid.exception.status, 502)
                saved = self.store.get(self.state["id"])
                self.assertEqual(saved["report"], report)
                self.assertIsNone(saved["acceptance_suite"])
        self.flow.generate_acceptance(self.state)
        self.assertTrue(self.state["acceptance_suite"]["cases"])

    def test_acceptance_survives_failed_prd_generation_and_clears_on_new_report(self):
        self.confirmed()
        self.flow.generate(self.state, False)
        self.flow.review_requirement(self.state, 0, "first_release", "任务可见", self.state["report_id"])
        self.flow.generate_acceptance(self.state)
        suite = copy.deepcopy(self.state["acceptance_suite"])
        self.model.fail = "writer"
        with self.assertRaises(AppError):
            self.flow.generate(self.state, False)
        self.assertEqual(self.store.get(self.state["id"])["acceptance_suite"], suite)

        self.model.fail = None
        self.flow.generate(self.state, False)
        self.assertNotEqual(self.state["report_id"], suite["report_id"])
        self.assertIsNone(self.state["acceptance_suite"])
        self.flow.review_requirement(self.state, 0, "first_release", "任务重新可见", self.state["report_id"])
        self.flow.generate_acceptance(self.state)
        self.flow.reopen(self.state)
        self.assertIsNone(self.store.get(self.state["id"])["acceptance_suite"])

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
