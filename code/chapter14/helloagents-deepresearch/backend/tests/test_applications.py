from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.applications import APPLICATION_STATUSES, ApplicationStore


class ApplicationStoreTests(unittest.TestCase):
    def test_save_application_persists_job_and_default_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))

            saved = store.save_application(
                {
                    "company": "示例公司",
                    "title": "Java 后端实习生",
                    "location": "上海",
                    "source_url": "https://example.com/jobs/1",
                    "requirements": ["Spring Boot"],
                    "match_score": 82,
                }
            )

            self.assertEqual(saved["application_status"], "待投递")
            self.assertEqual(saved["company"], "示例公司")
            self.assertEqual(saved["requirements"], ["Spring Boot"])
            self.assertEqual(saved["match_score"], 82)
            self.assertTrue(saved["id"].startswith("job_"))

            payload = json.loads((Path(tmp) / "applications.json").read_text("utf-8"))
            self.assertEqual(payload["items"][0]["id"], saved["id"])

    def test_save_same_source_url_updates_without_resetting_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))

            first = store.save_application(
                {
                    "id": "unstable-a",
                    "company": "示例公司",
                    "title": "后端实习",
                    "location": "上海",
                    "source_url": "https://example.com/jobs/1",
                },
                application_status="已投递",
            )
            second = store.save_application(
                {
                    "id": "unstable-b",
                    "company": "示例公司",
                    "title": "后端开发实习生",
                    "location": "上海",
                    "source_url": "https://example.com/jobs/1",
                }
            )

            items = store.list_applications()
            self.assertEqual(len(items), 1)
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(second["application_status"], "已投递")
            self.assertEqual(second["title"], "后端开发实习生")

    def test_update_application_validates_status_and_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))
            saved = store.save_application(
                {
                    "company": "示例公司",
                    "title": "AI 应用实习",
                    "location": "北京",
                }
            )

            updated = store.update_application(
                saved["id"],
                application_status="面试",
                status_note="一面约在周三",
            )

            self.assertEqual(updated["application_status"], "面试")
            self.assertEqual(updated["status_note"], "一面约在周三")
            with self.assertRaises(ValueError):
                store.update_application(saved["id"], application_status="随便看看")

    def test_delete_application_removes_saved_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))
            saved = store.save_application(
                {
                    "company": "示例公司",
                    "title": "前端实习",
                    "location": "杭州",
                }
            )

            self.assertTrue(store.delete_application(saved["id"]))
            self.assertFalse(store.delete_application(saved["id"]))
            self.assertEqual(store.list_applications(), [])

    def test_status_list_matches_initial_plan(self) -> None:
        self.assertEqual(
            APPLICATION_STATUSES,
            ("待投递", "已投递", "笔试", "面试", "拒绝", "Offer", "放弃"),
        )


if __name__ == "__main__":
    unittest.main()
