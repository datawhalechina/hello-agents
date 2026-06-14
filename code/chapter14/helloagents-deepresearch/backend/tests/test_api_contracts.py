from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main as main_module
from models import JobItem, SummaryStateOutput, TodoItem
from services.applications import ApplicationStore


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data:").strip())
        for line in body.splitlines()
        if line.startswith("data:")
    ]


class SuccessfulAgent:
    def __init__(self, *, config) -> None:
        self.config = config

    def run(self, topic: str) -> SummaryStateOutput:
        return SummaryStateOutput(
            running_summary="# 找实习行动报告",
            report_markdown="# 找实习行动报告",
            todo_items=[
                TodoItem(
                    id=1,
                    title="搜索岗位",
                    intent="找到可信岗位",
                    query=topic,
                    status="completed",
                    summary="完成",
                    sources_summary="https://example.com/job/1",
                )
            ],
            job_items=[
                JobItem(
                    id="job-1",
                    company="示例公司",
                    title="后端实习生",
                    location="上海",
                    source_url="https://example.com/job/1",
                    source_title="示例岗位",
                )
            ],
            search_diagnostics=[{"backend": "fake-search", "raw_count": 1}],
        )

    def run_stream(self, topic: str):
        yield {"type": "status", "message": "开始", "topic": topic}
        yield {
            "type": "final_report",
            "report": "# 找实习行动报告",
            "job_items": [],
            "search_diagnostics": [],
        }
        yield {"type": "done"}


class FailingStreamAgent(SuccessfulAgent):
    def run_stream(self, topic: str):
        yield {"type": "status", "message": "开始", "topic": topic}
        raise RuntimeError("stream contract boom")


class ApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        store = ApplicationStore(base_dir=Path(self.temp_dir.name))
        self.app = main_module.create_app(application_store=store)
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)
        self.temp_dir.cleanup()

    async def test_research_response_contract(self) -> None:
        with patch.object(main_module, "DeepResearchAgent", SuccessfulAgent):
            response = await self.client.post(
                "/research",
                json={"topic": "Java 后端实习"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {"report_markdown", "todo_items", "job_items", "search_diagnostics"},
        )
        self.assertEqual(payload["todo_items"][0]["status"], "completed")
        self.assertEqual(payload["job_items"][0]["source_url"], "https://example.com/job/1")

    async def test_research_configuration_error_is_http_400(self) -> None:
        with patch.object(
            main_module,
            "_build_config",
            side_effect=ValueError("unsupported test configuration"),
        ):
            response = await self.client.post("/research", json={"topic": "test"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "unsupported test configuration")

        with patch.object(
            main_module,
            "_build_config",
            side_effect=ValueError("unsupported stream configuration"),
        ):
            stream_response = await self.client.post(
                "/research/stream",
                json={"topic": "test"},
            )

        self.assertEqual(stream_response.status_code, 400)
        self.assertEqual(
            stream_response.json()["detail"],
            "unsupported stream configuration",
        )

    async def test_research_validation_error_is_http_422(self) -> None:
        response = await self.client.post("/research", json={})

        self.assertEqual(response.status_code, 422)

    async def test_stream_success_ends_with_done(self) -> None:
        with patch.object(main_module, "DeepResearchAgent", SuccessfulAgent):
            response = await self.client.post(
                "/research/stream",
                json={"topic": "Java 后端实习"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        events = _parse_sse_events(response.text)
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(any(event["type"] == "final_report" for event in events))

    async def test_stream_failure_ends_with_error(self) -> None:
        with patch.object(main_module, "DeepResearchAgent", FailingStreamAgent):
            response = await self.client.post(
                "/research/stream",
                json={"topic": "Java 后端实习"},
            )

        self.assertEqual(response.status_code, 200)
        events = _parse_sse_events(response.text)
        self.assertEqual(events[-1]["type"], "error")
        self.assertEqual(events[-1]["detail"], "stream contract boom")

    async def test_applications_crud_and_tracking_contract(self) -> None:
        create_response = await self.client.post(
            "/applications",
            json={
                "company": "示例公司",
                "title": "AI 应用实习",
                "location": "北京",
                "source_url": "https://example.com/jobs/ai",
                "application_status": "已投递",
                "application_channel": "内推",
                "applied_at": "2026-06-12",
                "next_action": "准备一面",
                "next_action_at": "2026-06-16",
                "resume_version": "resume-v2",
                "withdrawal_reason": "",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()
        self.assertEqual(created["application_channel"], "内推")
        self.assertEqual(created["next_action_at"], "2026-06-16")

        patch_response = await self.client.patch(
            f"/applications/{created['id']}",
            json={"next_action": "", "resume_version": "resume-v3"},
        )
        self.assertEqual(patch_response.status_code, 200)
        updated = patch_response.json()
        self.assertEqual(updated["next_action"], "")
        self.assertEqual(updated["resume_version"], "resume-v3")
        self.assertEqual(updated["application_channel"], "内推")

        list_response = await self.client.get("/applications")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["job_items"][0]["id"], created["id"])

        invalid_date = await self.client.patch(
            f"/applications/{created['id']}",
            json={"next_action_at": "2026/06/16"},
        )
        self.assertEqual(invalid_date.status_code, 400)
        self.assertIn("YYYY-MM-DD", invalid_date.json()["detail"])

        invalid_create = await self.client.post(
            "/applications",
            json={
                "company": "另一家公司",
                "title": "实习",
                "location": "上海",
                "applied_at": "2026-13-01",
            },
        )
        self.assertEqual(invalid_create.status_code, 400)

        delete_response = await self.client.delete(f"/applications/{created['id']}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"deleted": True})
        list_after_delete = await self.client.get("/applications")
        self.assertEqual(list_after_delete.json()["job_items"], [])


if __name__ == "__main__":
    unittest.main()
