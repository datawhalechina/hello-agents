from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from main import ResearchResponse
from models import JobItem, SummaryState, SummaryStateOutput, TodoItem
from services.job_extractor import JobExtractionService


class FakeExtractorAgent:
    def __init__(self, response: str, exc: Exception | None = None) -> None:
        self.response = response
        self.exc = exc
        self.prompt = ""
        self.cleared = False

    def run(self, prompt: str) -> str:
        self.prompt = prompt
        if self.exc:
            raise self.exc
        return self.response

    def clear_history(self) -> None:
        self.cleared = True


def make_state() -> SummaryState:
    return SummaryState(research_topic="找 2026 暑期 Java 后端实习，上海/杭州")


def make_task() -> TodoItem:
    return TodoItem(
        id=1,
        title="岗位搜索",
        intent="搜索 Java 后端实习岗位",
        query="2026 暑期 Java 后端 上海 杭州 招聘 JD",
    )


def make_service(
    response: str,
    exc: Exception | None = None,
) -> tuple[JobExtractionService, FakeExtractorAgent]:
    agent = FakeExtractorAgent(response, exc)
    service = JobExtractionService(
        lambda: agent,
        Configuration(
            llm_retry_base_delay=0,
            llm_retry_max_delay=0,
            llm_min_interval_seconds=0,
        ),
    )
    return service, agent


class JobExtractionServiceTests(unittest.TestCase):
    def test_valid_json_returns_job_items(self) -> None:
        payload = {
            "jobs": [
                {
                    "company": "示例科技",
                    "title": "Java 后端实习生",
                    "location": "上海",
                    "source_url": "https://www.zhipin.com/job_detail/abc.html",
                    "source_title": "示例科技 Java 后端实习生招聘",
                    "requirements": ["Spring Boot", "MySQL"],
                    "responsibilities": ["参与后端接口开发"],
                    "tech_stack": ["Java", "Redis"],
                    "duration": "2026 暑期",
                    "deadline": "未确认",
                    "match_score": 86,
                    "match_reason": "城市和技术栈匹配",
                    "resume_advice": ["突出 Spring Boot 项目"],
                    "risks": ["截止日期未确认"],
                }
            ]
        }
        service, agent = make_service(json.dumps(payload, ensure_ascii=False))

        jobs = service.extract_jobs(make_state(), make_task(), {"results": []}, "context")

        self.assertEqual(len(jobs), 1)
        self.assertIsInstance(jobs[0], JobItem)
        self.assertEqual(jobs[0].company, "示例科技")
        self.assertEqual(jobs[0].match_score, 86)
        self.assertTrue(agent.cleared)

    def test_bad_json_falls_back_to_source_only_jobs(self) -> None:
        search_result = {
            "results": [
                {
                    "title": "Java开发（26届暑期实习）招聘",
                    "url": "https://www.zhipin.com/job_detail/abc.html",
                }
            ]
        }
        service, _ = make_service("not json")

        jobs = service.extract_jobs(make_state(), make_task(), search_result, "context")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source_url, "https://www.zhipin.com/job_detail/abc.html")
        self.assertIsNone(jobs[0].match_score)
        self.assertIn("信息不足", jobs[0].match_reason)
        self.assertTrue(jobs[0].risks)

    def test_rate_limit_falls_back_to_reliable_source_only_jobs(self) -> None:
        search_result = {
            "results": [
                {
                    "title": "Java开发（26届暑期实习）招聘",
                    "url": "https://www.zhipin.com/job_detail/rate-limit.html",
                }
            ]
        }
        service, agent = make_service(
            "",
            RuntimeError("OpenAI API调用失败: Error code: 429 code 1302"),
        )

        jobs = service.extract_jobs(make_state(), make_task(), search_result, "context")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs[0].source_url,
            "https://www.zhipin.com/job_detail/rate-limit.html",
        )
        self.assertIsNone(jobs[0].match_score)
        self.assertTrue(agent.cleared)

    def test_deduplicates_by_source_url(self) -> None:
        payload = {
            "jobs": [
                {
                    "company": "A",
                    "title": "Java 后端实习",
                    "source_url": "https://www.zhipin.com/job_detail/repeat.html",
                    "source_title": "岗位 A 招聘",
                    "match_score": 80,
                },
                {
                    "company": "A",
                    "title": "Java 后端实习",
                    "source_url": "https://www.zhipin.com/job_detail/repeat.html",
                    "source_title": "岗位 A 招聘重复",
                    "match_score": 90,
                },
            ]
        }
        service, _ = make_service(json.dumps(payload, ensure_ascii=False))

        jobs = service.extract_jobs(make_state(), make_task(), {"results": []}, "context")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source_url, "https://www.zhipin.com/job_detail/repeat.html")

    def test_score_is_clamped_and_unknown_score_can_be_null(self) -> None:
        payload = {
            "jobs": [
                {
                    "company": "A",
                    "title": "Java 后端实习",
                    "source_url": "https://www.zhipin.com/job_detail/high.html",
                    "source_title": "高分岗位",
                    "match_score": 150,
                },
                {
                    "company": "B",
                    "title": "Java 后端实习",
                    "source_url": "https://www.shixiseng.com/intern/null",
                    "source_title": "待确认岗位",
                    "match_score": None,
                },
            ]
        }
        service, _ = make_service(json.dumps(payload, ensure_ascii=False))

        jobs = service.extract_jobs(make_state(), make_task(), {"results": []}, "context")
        scores = {job.source_url: job.match_score for job in jobs}

        self.assertEqual(scores["https://www.zhipin.com/job_detail/high.html"], 100)
        self.assertIsNone(scores["https://www.shixiseng.com/intern/null"])

    def test_bad_json_with_unreliable_sources_returns_empty_jobs(self) -> None:
        search_result = {
            "results": [
                {
                    "title": "用 Cursor 开发 10+ 项目后整理的提示词案例",
                    "url": "https://example.com/blog/rag-prompts",
                    "content": "博客 教程 提示词 案例",
                },
                {
                    "title": "从0到1快速搭建RAG应用",
                    "url": "https://example.com/tutorial/rag",
                    "content": "教程 学习资源 开源项目",
                },
            ]
        }
        service, _ = make_service("not json")

        jobs = service.extract_jobs(make_state(), make_task(), search_result, "context")

        self.assertEqual(jobs, [])

    def test_llm_non_job_sources_are_dropped(self) -> None:
        payload = {
            "jobs": [
                {
                    "company": "未确认",
                    "title": "从0到1快速搭建RAG应用",
                    "source_url": "https://example.com/tutorial/rag",
                    "source_title": "从0到1快速搭建RAG应用",
                    "match_score": None,
                }
            ]
        }
        service, _ = make_service(json.dumps(payload, ensure_ascii=False))

        jobs = service.extract_jobs(make_state(), make_task(), {"results": []}, "context")

        self.assertEqual(jobs, [])

    def test_response_models_keep_old_fields_and_include_job_items(self) -> None:
        output = SummaryStateOutput(
            running_summary="report",
            report_markdown="report",
            todo_items=[make_task()],
            job_items=[
                JobItem(
                    id="job_1",
                    company="A",
                    title="Java 后端实习",
                    source_url="https://example.com/job",
                    source_title="岗位 A",
                )
            ],
            search_diagnostics=[
                {
                    "task_id": 1,
                    "counts": {"raw": 1, "reliable": 1, "filtered": 0},
                }
            ],
        )

        response = ResearchResponse(
            report_markdown=output.report_markdown or "",
            todo_items=[{"id": item.id, "title": item.title} for item in output.todo_items],
            job_items=[item.__dict__ for item in output.job_items],
            search_diagnostics=output.search_diagnostics,
        )

        payload = response.model_dump()
        self.assertIn("report_markdown", payload)
        self.assertIn("todo_items", payload)
        self.assertIn("job_items", payload)
        self.assertIn("search_diagnostics", payload)
        self.assertEqual(payload["job_items"][0]["id"], "job_1")
        self.assertEqual(payload["search_diagnostics"][0]["counts"]["reliable"], 1)


if __name__ == "__main__":
    unittest.main()
