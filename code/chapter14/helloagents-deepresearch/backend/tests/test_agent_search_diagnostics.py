from __future__ import annotations

import sys
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import agent as agent_module
from agent import DeepResearchAgent
from config import Configuration
from models import JobItem, SummaryState, TodoItem


class FakeJobExtractor:
    def __init__(self, jobs=None) -> None:
        self.jobs = jobs or []

    def extract_jobs(self, *_args, **_kwargs):
        return self.jobs


class FakeSummarizer:
    def summarize_task(self, *_args, **_kwargs) -> str:
        return "summary"

    def stream_task_summary(self, *_args, **_kwargs):
        return iter(["summary"]), lambda: "summary"


class AgentSearchDiagnosticsTests(unittest.TestCase):
    def test_job_search_retries_with_platform_query_when_no_reliable_results(self) -> None:
        coordinator = object.__new__(DeepResearchAgent)
        coordinator.config = Configuration()
        coordinator._state_lock = Lock()
        coordinator._last_search_notices = []
        coordinator.job_extractor = FakeJobExtractor()
        coordinator.summarizer = FakeSummarizer()
        coordinator._drain_tool_events = lambda *_args, **_kwargs: []

        state = SummaryState(run_id="test_run", research_topic="找 Java 后端实习")
        task = TodoItem(
            id=1,
            title="岗位搜索",
            intent="搜索实习岗位",
            query="Java 后端 实习 上海",
        )

        calls: list[str] = []

        def fake_dispatch(query, _config, _loop_count):
            calls.append(query)
            if len(calls) == 1:
                return (
                    {
                        "results": [
                            {
                                "title": "Spring Boot 教程",
                                "url": "https://example.com/blog",
                                "content": "教程 博客",
                            }
                        ]
                    },
                    [],
                    None,
                    "duckduckgo",
                )
            return (
                {
                    "results": [
                        {
                            "title": "Java开发（26届暑期实习）招聘",
                            "url": "https://www.zhipin.com/job_detail/abc.html",
                            "content": "岗位职责 任职要求 投递",
                        }
                    ]
                },
                [],
                None,
                "duckduckgo",
            )

        with patch.object(agent_module, "dispatch_search", side_effect=fake_dispatch):
            list(coordinator._execute_task(state, task, emit_stream=False))

        self.assertEqual(len(calls), 2)
        self.assertIn("岗位详情", calls[0])
        self.assertIn("BOSS直聘", calls[1])
        self.assertEqual(task.status, "completed")
        self.assertEqual(len(state.search_diagnostics), 1)
        diagnostics = state.search_diagnostics[0]
        self.assertEqual(diagnostics["counts"]["raw"], 2)
        self.assertEqual(diagnostics["counts"]["reliable"], 1)
        self.assertEqual(diagnostics["retry_query"], calls[1])

    def test_job_items_event_uses_merged_snapshot(self) -> None:
        coordinator = object.__new__(DeepResearchAgent)
        coordinator.config = Configuration()
        coordinator._state_lock = Lock()
        coordinator._last_search_notices = []
        coordinator.job_extractor = FakeJobExtractor(
            [
                JobItem(
                    id="job_1",
                    company="示例科技",
                    title="Java 后端实习",
                    source_url="https://www.zhipin.com/job_detail/abc.html",
                    source_title="Java 后端实习招聘",
                )
            ]
        )
        coordinator.summarizer = FakeSummarizer()
        coordinator._drain_tool_events = lambda *_args, **_kwargs: []

        state = SummaryState(run_id="test_run", research_topic="找 Java 后端实习")
        task = TodoItem(
            id=1,
            title="岗位搜索",
            intent="搜索实习岗位",
            query="Java 后端 实习 上海",
        )

        def fake_dispatch(_query, _config, _loop_count):
            return (
                {
                    "results": [
                        {
                            "title": "Java开发（26届暑期实习）招聘",
                            "url": "https://www.zhipin.com/job_detail/abc.html",
                            "content": "岗位职责 任职要求 投递",
                        }
                    ]
                },
                [],
                None,
                "duckduckgo",
            )

        with patch.object(agent_module, "dispatch_search", side_effect=fake_dispatch):
            events = list(coordinator._execute_task(state, task, emit_stream=True, step=1))

        job_event = next(event for event in events if event["type"] == "job_items")
        self.assertEqual(job_event["jobs"][0]["id"], "job_1")
        self.assertEqual(job_event["all_jobs"][0]["id"], "job_1")
        self.assertEqual(state.job_items[0].id, "job_1")


if __name__ == "__main__":
    unittest.main()
