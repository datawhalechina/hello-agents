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
        self.request(path + "/confirm", {"brief": BRIEF})
        self.request(path + "/generate", {"online": False})
        self.wait(state["id"])
        self.request(path + "/reopen", {})
        self.assertEqual(self.request(path + "/export")[0], 409)

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
