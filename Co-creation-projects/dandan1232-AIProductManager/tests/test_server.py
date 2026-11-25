"""HTTP integration tests run a real local server; external services are explicit doubles."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.config import Settings
from src.server import Application, make_server
from tests.support import BRIEF, ModelDouble, SearchDouble


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.model = ModelDouble()
        self.app = Application(Settings(model="test-model", api_key="test-secret", search_key="test-search"),
                               Path(self.temp.name) / "projects.sqlite3", lambda _: self.model, lambda _: SearchDouble())
        self.server = make_server(self.app, 0)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        # No daemon worker should retain a temporary DB at teardown.
        deadline = time.monotonic() + 5
        while any(p["busy"] for p in self.app.store.list()) and time.monotonic() < deadline:
            time.sleep(.01)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, path, body=None, extra_headers=None):
        headers = {"Content-Type": "application/json", "X-Requested-With": "AIProductManager"}
        headers.update(extra_headers or {})
        req = Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            data = response.read()
            parsed = json.loads(data) if "application/json" in response.headers.get("Content-Type", "") else data
            return response.status, parsed, response.headers

    def wait(self, project_id):
        for _ in range(100):
            _, state, _ = self.request("/api/projects/" + project_id)
            if not state["busy"]:
                return state
            time.sleep(.01)
        self.fail("background job did not finish")

    def create(self):
        status, state, _ = self.request("/api/projects", {"idea": "我希望自己管理任务，不做支付"})
        self.assertEqual(status, 200)
        return self.wait(state["id"])

    def test_full_http_flow_and_download(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": True})[0], 200)
        done = self.wait(state["id"])
        self.assertEqual(done["stage"], "done")
        self.assertFalse(done["error"])
        status, data, headers = self.request(path + "/export")
        self.assertEqual(status, 200)
        self.assertIn("不做支付", data.decode())
        self.assertIn("attachment", headers["Content-Disposition"])

    def test_saved_draft_and_answer_edits_survive_interview_and_reach_report(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        title = "我自己填写的项目名称"
        problem = "漏掉交接时的关键任务"
        original_question = "哪些人负责接手？"
        updated_question = "是否需要自动安排交接时间？"
        status, _, _ = self.request(path + "/draft", {
            "edits": {"title": title}, "pending_questions": [original_question],
        })
        self.assertEqual(status, 200)
        refreshed = self.request(path)[1]
        self.assertEqual(refreshed["brief"]["title"], title)
        self.assertIsNone(refreshed["confirmed_brief"])
        self.assertEqual(refreshed["pending_questions"], [original_question])

        answer = "主要在交接时添加任务"
        status, _, _ = self.request(path + "/answer", {
            "answer": answer, "edits": {"problem": problem}, "pending_questions": [updated_question],
        })
        self.assertEqual(status, 200)
        interviewed = self.wait(state["id"])
        self.assertFalse(interviewed["error"])
        self.assertEqual(interviewed["messages"][-2]["content"], answer)
        self.assertEqual(interviewed["brief"]["title"], title)
        self.assertEqual(interviewed["brief"]["problem"], problem)
        self.assertEqual(interviewed["draft_suggestions"]["title"], BRIEF["title"])
        self.assertEqual(interviewed["draft_suggestions"]["problem"], BRIEF["problem"])
        self.assertEqual(interviewed["pending_questions"], [updated_question])
        self.assertIsNone(interviewed["confirmed_brief"])

        status, confirmed, _ = self.request(path + "/confirm", {
            "brief": interviewed["brief"], "pending_questions": interviewed["pending_questions"],
        })
        self.assertEqual(status, 200)
        self.assertEqual(confirmed["confirmed_brief"]["title"], title)
        self.assertEqual(confirmed["confirmed_questions"], [updated_question])
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        done = self.wait(state["id"])
        self.assertFalse(done["error"])
        writer_context = next(context for role, context in self.model.calls if role == "writer")
        self.assertEqual(writer_context["confirmed_questions"], [updated_question])
        status, data, _ = self.request(path + "/export")
        self.assertEqual(status, 200)
        self.assertIn(updated_question, data.decode())
        self.assertNotIn(original_question, data.decode())

    def test_confirmation_without_question_edits_keeps_interview_assumptions(self):
        state = self.create()
        self.assertTrue(state["assumptions"])
        path = "/api/projects/" + state["id"]
        status, confirmed, _ = self.request(path + "/confirm", {"brief": state["brief"]})
        self.assertEqual(status, 200)
        self.assertEqual(confirmed["confirmed_questions"], state["assumptions"])

    def test_legacy_report_without_review_fields_is_reviewable(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        legacy = self.wait(state["id"])
        for field in ("report_id", "report_generated_at", "prd_reviews", "confirmed_questions",
                      "pending_questions", "manual_brief", "draft_suggestions"):
            legacy.pop(field, None)
        self.app.store.save(legacy)
        status, error, _ = self.request(path + "/release-checklist")
        self.assertEqual(status, 409)
        self.assertIn("首版做", error["error"])

        acceptance = "交接人打开自己的任务列表后可以看到刚保存的任务。"
        review = {"index": 0, "decision": "first_release", "acceptance": acceptance, "report_id": None}
        status, reviewed, _ = self.request(path + "/review", review)
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["prd_reviews"]["0"], {"decision": "first_release", "acceptance": acceptance})
        status, data, _ = self.request(path + "/export")
        self.assertEqual(status, 200)
        self.assertIn(acceptance, data.decode())
        self.assertIn("评审决定：首版做", data.decode())
        status, data, _ = self.request(path + "/release-checklist")
        self.assertEqual(status, 200)
        self.assertIn(acceptance, data.decode())

    def test_release_checklist_exports_only_saved_first_release_items_in_prd_order(self):
        original = self.model.run

        def writer_with_multiple_requirements(role, context):
            result = original(role, context)
            if role == "writer":
                result["requirements"].extend([
                    {"name": "查看任务", "description": "打开列表查看任务", "acceptance": "展示原有的列表"},
                    {"name": "提醒任务", "description": "显示提醒弹窗", "acceptance": "弹出提醒"},
                    {"name": "搜索任务", "description": "用关键词定位任务", "acceptance": "展示搜索结果"},
                    {"name": "归档任务", "description": "保存到归档列表", "acceptance": "查看归档列表"},
                ])
            return result

        self.model.run = writer_with_multiple_requirements
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        done = self.wait(state["id"])
        self.assertEqual(done["stage"], "done")

        acceptance_list = "打开任务页面后按时间倒序排列。\n空列表有明确提示。"
        acceptance_search = "搜索关键词后只展示名称匹配的任务。"
        for index, decision, acceptance in (
            (3, "first_release", acceptance_search),
            (0, "later", "后续支持新增任务。"),
            (2, "pending", "待决定是否展示提醒。"),
            (1, "first_release", acceptance_list),
        ):
            self.assertEqual(self.request(path + "/review", {
                "index": index, "decision": decision, "acceptance": acceptance, "report_id": done["report_id"],
            })[0], 200)

        status, data, headers = self.request(path + "/release-checklist")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/markdown; charset=utf-8")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="first-release-checklist.md"')
        checklist = data.decode()
        self.assertEqual([line for line in checklist.splitlines() if line.startswith("- [ ]")],
                         ["- [ ] **F02 查看任务**", "- [ ] **F04 搜索任务**"])
        self.assertIn("打开列表查看任务", checklist)
        self.assertIn("用关键词定位任务", checklist)
        self.assertIn(acceptance_list.replace("\n", "\n    "), checklist)
        self.assertIn(acceptance_search, checklist)
        for excluded in ("展示原有的列表", "展示搜索结果", "新增任务", "提醒任务", "归档任务"):
            self.assertNotIn(excluded, checklist)
        self.assertIn("F02 查看任务", self.request(path + "/export")[1].decode())

    def test_acceptance_cases_record_status_export_and_expire_on_scope_change(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/generate-acceptance", {})[0], 409)
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        report = self.wait(state["id"])
        self.assertEqual(self.request(path + "/generate-acceptance", {})[0], 409)

        acceptance = "新建任务后刷新，列表仍显示任务名称。"
        review = {"index": 0, "decision": "first_release", "acceptance": acceptance, "report_id": report["report_id"]}
        self.assertEqual(self.request(path + "/review", review)[0], 200)
        self.assertEqual(self.request(path + "/generate-acceptance", {})[0], 200)
        generated = self.wait(state["id"])
        suite = generated["acceptance_suite"]
        self.assertEqual(suite["report_id"], report["report_id"])
        self.assertEqual(suite["cases"][0]["status"], "pending")
        self.assertEqual(suite["cases"][0]["acceptance"], acceptance)
        self.assertEqual(self.request(path + "/generate-acceptance", {})[0], 409)

        mark = {"suite_id": suite["id"], "requirement_id": "F01", "status": "needs_fix"}
        self.assertEqual(self.request(path + "/mark-acceptance", {**mark, "status": "typo"})[0], 400)
        self.assertEqual(self.request(path + "/mark-acceptance", mark)[0], 200)
        restored = self.request(path)[1]
        self.assertEqual(restored["acceptance_suite"]["cases"][0]["status"], "needs_fix")
        self.assertEqual(restored["report"], generated["report"])

        status, data, headers = self.request(path + "/acceptance-export")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="first-release-acceptance.md"')
        markdown = data.decode()
        for text in ("F01 新增任务", "待修复", acceptance, "1. 填写测试数据", "预期结果"):
            self.assertIn(text, markdown)

        self.assertEqual(self.request(path + "/review", review)[0], 200)
        self.assertEqual(self.request(path + "/acceptance-export")[0], 200)
        self.assertEqual(self.request(path + "/review", {**review, "acceptance": "重新确认的新验收条件"})[0], 200)
        self.assertEqual(self.request(path + "/mark-acceptance", mark)[0], 409)
        self.assertEqual(self.request(path + "/acceptance-export")[0], 409)

    def test_failed_acceptance_generation_retries_without_rewriting_prd(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        report = self.wait(state["id"])
        review = {"index": 0, "decision": "first_release", "acceptance": "确认可以新建任务", "report_id": report["report_id"]}
        status, reviewed, _ = self.request(path + "/review", review)
        self.assertEqual(status, 200)

        self.model.fail = "acceptance"
        self.assertEqual(self.request(path + "/generate-acceptance", {})[0], 200)
        failed = self.wait(state["id"])
        self.assertTrue(failed["error"])
        self.assertEqual(failed["report"], reviewed["report"])
        self.assertEqual(self.request(path + "/acceptance-export")[0], 409)

        self.model.fail = None
        self.assertEqual(self.request(path + "/retry", {})[0], 200)
        retried = self.wait(state["id"])
        self.assertFalse(retried["error"])
        self.assertEqual(retried["report_id"], report["report_id"])
        self.assertEqual(retried["acceptance_suite"]["cases"][0]["status"], "pending")
        self.assertEqual(sum(role == "writer" for role, _ in self.model.calls), 1)

    def test_invalid_and_stale_reviews_leave_export_and_review_intact(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/confirm", {"brief": BRIEF})[0], 200)
        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        done = self.wait(state["id"])
        review = {"index": 0, "decision": "later", "acceptance": "后续支持查看任务记录。", "report_id": done["report_id"]}
        status, saved, _ = self.request(path + "/review", review)
        self.assertEqual(status, 200)
        for invalid in ({"index": 99}, {"decision": "unknown"}, {"acceptance": 1}):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.request(path + "/review", {**review, **invalid})[0], 400)
        restored = self.request(path)[1]
        self.assertEqual(restored["prd_reviews"], saved["prd_reviews"])
        self.assertEqual(self.request(path + "/export")[1].decode(), saved["report"])

        self.assertEqual(self.request(path + "/generate", {"online": False})[0], 200)
        regenerated = self.wait(state["id"])
        self.assertTrue(regenerated["report_id"])
        self.assertNotEqual(regenerated["report_id"], done["report_id"])
        self.assertEqual(self.request(path + "/review", review)[0], 409)
        self.assertEqual(self.request(path + "/export")[1].decode(), regenerated["report"])

    def test_settings_response_and_database_do_not_include_credentials(self):
        status, value, _ = self.request("/api/settings", {"model": "new-model", "api_key": "new-private-secret"})
        self.assertEqual(status, 200)
        self.assertNotIn("new-private-secret", str(value))
        state = self.create()
        self.assertNotIn("new-private-secret", json.dumps(state))
        self.assertNotIn("new-private-secret", Path(self.app.store.path).read_bytes().decode(errors="ignore"))

    def test_no_report_before_generation_or_after_reopening(self):
        state = self.create()
        path = "/api/projects/" + state["id"]
        self.assertEqual(self.request(path + "/export")[0], 409)
        status, error, _ = self.request(path + "/release-checklist")
        self.assertEqual(status, 409)
        self.assertIn("文档生成完成", error["error"])
        self.request(path + "/confirm", {"brief": BRIEF})
        self.request(path + "/generate", {"online": False})
        self.wait(state["id"])
        self.assertEqual(self.request(path + "/release-checklist")[0], 409)
        self.request(path + "/reopen", {})
        self.assertEqual(self.request(path + "/export")[0], 409)
        self.assertEqual(self.request(path + "/release-checklist")[0], 409)

    def test_cross_origin_mutation_rejected(self):
        status, _, _ = self.request("/api/projects", {"idea": "跨站提交测试"}, {"Origin": "https://example.com"})
        self.assertEqual(status, 403)

    def test_private_files_not_served(self):
        for path in ("/.env", "/runtime/projects.sqlite3", "/../src/config.py"):
            self.assertEqual(self.request(path)[0], 404)

    def test_duplicate_mutation_blocked_during_model_request(self):
        started, release = threading.Event(), threading.Event()
        original = self.model.run
        def block(role, context):
            started.set()
            release.wait(3)
            return original(role, context)
        self.model.run = block
        _, state, _ = self.request("/api/projects", {"idea": "并发测试任务管理工具"})
        self.assertTrue(started.wait(1))
        try:
            status, _, _ = self.request(f"/api/projects/{state['id']}/confirm", {"brief": BRIEF})
            self.assertEqual(status, 409)
        finally:
            release.set()
        self.wait(state["id"])

    def test_retry_does_not_duplicate_user_message(self):
        self.model.fail = "interview"
        state = self.create()
        self.assertTrue(state["error"])
        self.model.fail = None
        self.request(f"/api/projects/{state['id']}/retry", {})
        result = self.wait(state["id"])
        self.assertFalse(result["error"])
        self.assertEqual(sum(m["role"] == "user" for m in result["messages"]), 1)

    def test_missing_search_key_requires_explicit_offline_choice(self):
        state = self.create()
        self.request(f"/api/projects/{state['id']}/confirm", {"brief": BRIEF})
        self.app.settings.search_key = ""
        self.assertEqual(self.request(f"/api/projects/{state['id']}/generate", {"online": True})[0], 503)
        self.assertEqual(self.request(f"/api/projects/{state['id']}/generate", {"online": False})[0], 200)
        self.wait(state["id"])

    def test_static_ui_and_security_headers(self):
        status, page, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("AI 产品经理", page.decode())
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
