"""Regression tests for synchronous and streaming research execution."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent import DeepResearchAgent
from config import Configuration
from main import create_app
from models import TodoItem


class ResearchExecutionTests(unittest.TestCase):
    """Exercise the real task executor without model or search requests."""

    def setUp(self):
        self.config = Configuration(enable_notes=False)
        with patch("agent.HelloAgentsLLM"), patch("agent.ToolAwareSimpleAgent"):
            self.agent = DeepResearchAgent(config=self.config)

        self.tasks = [
            TodoItem(id=1, title="First task", intent="Find evidence", query="first query"),
            TodoItem(id=2, title="Second task", intent="Compare evidence", query="second query"),
        ]
        self.agent.planner.plan_todo_list = Mock(return_value=self.tasks)
        self.agent.summarizer.summarize_task = Mock(
            side_effect=lambda state, task, context: f"Summary {task.id}"
        )
        self.agent.summarizer.stream_task_summary = Mock(
            side_effect=lambda state, task, context: (
                iter([f"Summary {task.id}"]), lambda: f"Summary {task.id}"
            )
        )
        self.agent.reporting.generate_report = Mock(
            side_effect=lambda state: " | ".join(task.summary or "Missing" for task in state.todo_items)
        )
        search_patch = patch(
            "agent.dispatch_search",
            return_value=(
                {"results": [{"title": "Evidence", "url": "https://example.com/source", "content": "Facts"}]},
                [], None, "test",
            ),
        )
        self.search = search_patch.start()
        self.addCleanup(search_patch.stop)

    def test_run_researches_every_task_before_generating_report(self):
        result = self.agent.run("Research topic")

        self.search.assert_has_calls([
            call("first query", self.config, 0),
            call("second query", self.config, 1),
        ])
        self.assertEqual(self.agent.summarizer.summarize_task.call_count, 2)
        self.assertEqual([task.status for task in result.todo_items], ["completed", "completed"])
        self.assertTrue(all("https://example.com/source" in task.sources_summary for task in result.todo_items))
        self.assertEqual(result.report_markdown, "Summary 1 | Summary 2")
        report_state = self.agent.reporting.generate_report.call_args.args[0]
        self.assertEqual(report_state.research_loop_count, 2)
        self.assertEqual(len(report_state.web_research_results), 2)

    def test_run_skips_a_task_when_search_returns_no_results(self):
        self.agent.planner.plan_todo_list.return_value = self.tasks[:1]
        self.search.return_value = ({"results": []}, [], None, "test")

        result = self.agent.run("Research topic")

        self.search.assert_called_once()
        self.agent.summarizer.summarize_task.assert_not_called()
        self.assertEqual(result.todo_items[0].status, "skipped")
        self.assertIsNone(result.todo_items[0].summary)
        self.agent.reporting.generate_report.assert_called_once()

    def test_run_executes_the_fallback_task_when_planning_returns_nothing(self):
        self.agent.planner.plan_todo_list.return_value = []

        result = self.agent.run("Research topic")

        self.assertEqual(len(result.todo_items), 1)
        self.search.assert_called_once_with(result.todo_items[0].query, self.config, 0)
        self.assertEqual(result.todo_items[0].status, "completed")
        self.assertEqual(result.report_markdown, "Summary 1")

    def test_stream_still_researches_tasks_and_emits_the_completed_report(self):
        events = list(self.agent.run_stream("Research topic"))

        completed = [event for event in events
                     if event["type"] == "task_status" and event["status"] == "completed"]
        self.assertEqual(self.search.call_count, 2)
        self.assertEqual(self.agent.summarizer.stream_task_summary.call_count, 2)
        self.agent.summarizer.summarize_task.assert_not_called()
        self.assertEqual(sorted(event["task_id"] for event in completed), [1, 2])
        reports = [event["report"] for event in events if event["type"] == "final_report"]
        self.assertEqual(reports, ["Summary 1 | Summary 2"])
        self.assertEqual(events[-1], {"type": "done"})

    def test_research_endpoint_returns_completed_tasks_with_evidence(self):
        with patch("main.DeepResearchAgent", return_value=self.agent):
            response = TestClient(create_app()).post("/research", json={"topic": "Research topic"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(self.search.call_count, 2)
        self.assertEqual([task["status"] for task in payload["todo_items"]], ["completed", "completed"])
        self.assertTrue(all("https://example.com/source" in task["sources_summary"] for task in payload["todo_items"]))
        self.assertEqual(payload["report_markdown"], "Summary 1 | Summary 2")


if __name__ == "__main__":
    unittest.main()
