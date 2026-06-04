from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from main import create_app
from note_tool import NoteTool
from search_tool import SearchTool


class ConfigurationSecurityTests(unittest.TestCase):
    def test_default_cors_origins_cover_local_vite_ports(self) -> None:
        origins = Configuration().resolved_cors_origins()

        self.assertIn("http://localhost:5173", origins)
        self.assertIn("http://localhost:5174", origins)
        self.assertIn("http://127.0.0.1:5173", origins)
        self.assertIn("http://127.0.0.1:5174", origins)

    def test_cors_allow_origins_env_overrides_defaults(self) -> None:
        with patch.dict(
            "os.environ",
            {"CORS_ALLOW_ORIGINS": "http://example.test, http://localhost:3000"},
        ):
            origins = Configuration.from_env().resolved_cors_origins()

        self.assertEqual(origins, ["http://example.test", "http://localhost:3000"])

    def test_app_uses_configured_cors_origins(self) -> None:
        with patch.dict("os.environ", {"CORS_ALLOW_ORIGINS": "http://example.test"}):
            app = create_app()

        cors_middleware = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls.__name__ == "CORSMiddleware"
        )
        self.assertEqual(cors_middleware.kwargs["allow_origins"], ["http://example.test"])

    def test_unimplemented_search_backend_returns_clear_notice(self) -> None:
        tool = SearchTool()

        def fake_duckduckgo(query: str, *, max_results: int, backend: str):
            return {
                "results": [],
                "backend": backend,
                "answer": None,
                "notices": [],
            }

        with patch.object(tool, "_duckduckgo", side_effect=fake_duckduckgo):
            payload = tool.run({"input": "Java 实习", "backend": "perplexity"})

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["backend"], "duckduckgo")
        self.assertIn("当前搜索后端 perplexity 暂未实现", payload["notices"][0])
        self.assertIn("已降级为 DuckDuckGo", payload["notices"][0])

    def test_note_paths_stay_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = NoteTool(workspace=tmpdir)
            path = tool._path_for("../../../etc/passwd")

            workspace = Path(tmpdir).resolve()
            self.assertTrue(path.is_absolute())
            self.assertEqual(path.parent, workspace)
            self.assertTrue(path.name.endswith(".md"))


if __name__ == "__main__":
    unittest.main()
