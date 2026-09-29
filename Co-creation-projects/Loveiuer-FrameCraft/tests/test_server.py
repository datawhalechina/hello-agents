import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from d2c import server
from d2c.artifacts import validate_files, write_result


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(server, "RUN_ROOT", Path(self.temp.name) / "runs")
        self.root_patch.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.client.close()
        self.root_patch.stop()
        self.temp.cleanup()

    def test_full_demo_preview_files_download(self):
        response = self.client.post("/api/runs", json={"source": "sample", "mode": "demo"})
        self.assertEqual(response.status_code, 202, response.text)
        run_id = response.json()["id"]
        run = self.client.get(f"/api/runs/{run_id}").json()
        self.assertEqual(run["status"], "completed", run.get("error"))
        self.assertTrue(run["events"])
        self.assertEqual(run["result"]["mode"], "demo")
        paths = {item["path"] for item in run["result"]["files"]}
        self.assertTrue({"src/App.tsx", "preview.html", "review-report.json"} <= paths)
        preview = self.client.get(f"/api/runs/{run_id}/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("sandbox", preview.headers["content-security-policy"])
        source = self.client.get(f"/api/runs/{run_id}/files", params={"path": "src/App.tsx"})
        self.assertIn("data-node-id", source.text)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/files", params={"path": "../../.env"}).status_code, 404)
        archive = self.client.get(f"/api/runs/{run_id}/download")
        with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
            self.assertTrue(paths <= set(zipped.namelist()))
            report = json.loads(zipped.read("review-report.json"))
            self.assertEqual(report["mode"], "demo")

    def test_invalid_import_becomes_failed_run(self):
        response = self.client.post("/api/runs", json={"source": "json", "payload": {}})
        run = self.client.get("/api/runs/" + response.json()["id"]).json()
        self.assertEqual(run["status"], "failed")
        self.assertTrue(run["error"])
        self.assertEqual(self.client.get("/api/runs/" + run["id"] + "/download").status_code, 409)

    def test_missing_credentials_do_not_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(self.client.get("/api/health").json()["live_available"])
            self.assertEqual(self.client.post("/api/runs", json={"mode": "live"}).status_code, 400)
            self.assertEqual(self.client.post("/api/runs", json={"source": "figma", "figma_url": "https://figma.com/design/abc?node-id=1-2"}).status_code, 400)

    def test_validation_and_cross_site_guard(self):
        self.assertEqual(self.client.post("/api/runs", json={"source": "json"}).status_code, 400)
        self.assertEqual(self.client.post("/api/runs", json={"mode": "unknown"}).status_code, 422)
        self.assertEqual(self.client.post("/api/runs", json={}, headers={"origin": "https://evil.test"}).status_code, 403)
        self.assertEqual(self.client.get("/api/runs/invalid").status_code, 404)
        self.assertEqual(self.client.post("/api/runs", content=b"x" * (2 * 1024 * 1024 + 1)).status_code, 413)

    def test_concurrency_limit(self):
        self.assertTrue(server._slots.acquire(False))
        self.assertTrue(server._slots.acquire(False))
        try:
            self.assertEqual(self.client.post("/api/runs", json={}).status_code, 429)
        finally:
            server._slots.release()
            server._slots.release()

    def test_secret_error_redacted(self):
        with patch.dict("os.environ", {"LLM_API_KEY": "test-secret-value"}):
            self.assertNotIn("test-secret-value", server._safe_error(RuntimeError("key test-secret-value failed")))

    def test_artifact_path_guard_and_no_overwrite(self):
        for path in ("../../secrets.txt", "/tmp/escape", "src\\escape"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_files({path: "bad"})
        result = {"files": {"test.txt": "hello"}, "design": {}, "events": [], "review": {}, "metrics": {}, "mode": "demo", "plan": {}}
        output = Path(self.temp.name) / "project"
        write_result(result, output)
        with self.assertRaises(FileExistsError):
            write_result(result, output)
        self.assertEqual((output / "test.txt").read_text(), "hello")


if __name__ == "__main__":
    unittest.main()
