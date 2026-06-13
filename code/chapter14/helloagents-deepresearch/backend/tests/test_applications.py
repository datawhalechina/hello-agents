from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.applications import (
    APPLICATION_STATUSES,
    TRACKING_FIELDS,
    ApplicationStore,
)


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
            self.assertTrue(all(saved[field] == "" for field in TRACKING_FIELDS))

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
                application_channel="官网",
                next_action="准备笔试",
                next_action_at="2026-06-18",
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
            self.assertEqual(second["application_channel"], "官网")
            self.assertEqual(second["next_action"], "准备笔试")
            self.assertEqual(second["next_action_at"], "2026-06-18")
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

    def test_tracking_fields_support_partial_update_and_explicit_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))
            saved = store.save_application(
                {
                    "company": "示例公司",
                    "title": "测试开发实习",
                    "location": "深圳",
                },
                application_channel="内推",
                applied_at="2026-06-12",
                next_action="跟进面试安排",
                next_action_at="2026-06-16",
                resume_version="resume-v3",
                withdrawal_reason="暂不适用",
            )

            updated = store.update_application(
                saved["id"],
                next_action="",
                withdrawal_reason="",
            )

            self.assertEqual(updated["application_channel"], "内推")
            self.assertEqual(updated["applied_at"], "2026-06-12")
            self.assertEqual(updated["next_action"], "")
            self.assertEqual(updated["next_action_at"], "2026-06-16")
            self.assertEqual(updated["resume_version"], "resume-v3")
            self.assertEqual(updated["withdrawal_reason"], "")

    def test_tracking_dates_must_use_iso_date_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ApplicationStore(base_dir=Path(tmp))
            with self.assertRaisesRegex(ValueError, "applied_at must use YYYY-MM-DD"):
                store.save_application(
                    {"company": "示例公司", "title": "实习", "location": "北京"},
                    applied_at="2026/06/12",
                )

            saved = store.save_application(
                {"company": "示例公司", "title": "实习", "location": "北京"}
            )
            with self.assertRaisesRegex(ValueError, "next_action_at must use YYYY-MM-DD"):
                store.update_application(saved["id"], next_action_at="2026-02-30")

    def test_legacy_json_records_receive_empty_tracking_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "applications.json"
            path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "legacy-job",
                                "company": "旧记录公司",
                                "title": "旧岗位",
                                "location": "上海",
                                "application_status": "待投递",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            item = ApplicationStore(base_dir=Path(tmp)).list_applications()[0]

            self.assertEqual(item["id"], "legacy-job")
            self.assertTrue(all(item[field] == "" for field in TRACKING_FIELDS))

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
