from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import SummaryState, TodoItem
from services.reporter import ReportingService


def test_config() -> Configuration:
    return Configuration(
        llm_retry_base_delay=0,
        llm_retry_max_delay=0,
        llm_min_interval_seconds=0,
    )


class FakeReportAgent:
    def __init__(self, response: str = "", exc: Exception | None = None) -> None:
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
    return SummaryState(
        research_topic="找 2026 暑期 Java 后端实习，上海/杭州",
        todo_items=[
            TodoItem(
                id=1,
                title="岗位搜索",
                intent="搜索岗位",
                query="Java 后端 实习 招聘",
                status="completed",
                summary="发现若干 Java 后端实习岗位线索。",
                sources_summary="* 岗位 A : https://example.com/a",
            )
        ],
    )


class ReportingServiceTests(unittest.TestCase):
    def test_llm_failure_returns_fallback_report(self) -> None:
        agent = FakeReportAgent(exc=RuntimeError("timeout"))
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state())

        self.assertTrue(report.startswith("# 找实习行动报告"))
        self.assertIn("后端兜底模板", report)
        self.assertIn("岗位搜索", report)
        self.assertTrue(agent.cleared)

    def test_empty_llm_response_returns_fallback_report(self) -> None:
        agent = FakeReportAgent(response="")
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state())

        self.assertTrue(report.startswith("# 找实习行动报告"))
        self.assertNotIn("报告生成失败", report)

    def test_long_task_material_is_truncated_before_prompt(self) -> None:
        state = make_state()
        state.todo_items[0].summary = "x" * 3000
        agent = FakeReportAgent(response="# 找实习行动报告\n\nOK")
        service = ReportingService(agent, test_config())

        report = service.generate_report(state)

        self.assertTrue(report.startswith("# 找实习行动报告"))
        self.assertIn("[已截断，保留关键摘要]", agent.prompt)
        self.assertLess(len(agent.prompt), 2600)


if __name__ == "__main__":
    unittest.main()
