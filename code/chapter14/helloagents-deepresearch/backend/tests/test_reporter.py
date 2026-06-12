from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import JobItem, SummaryState, TodoItem
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


def make_state_with_jobs() -> SummaryState:
    state = make_state()
    state.job_items = [
        JobItem(
            id="job_low",
            company="低分科技",
            title="后端研发实习生",
            location="杭州",
            source_url="https://jobs.example.com/low",
            source_title="低分科技后端研发实习生",
            requirements=["Java"],
            responsibilities=["参与接口开发"],
            tech_stack=["Java"],
            duration="2026 暑期",
            deadline="未确认",
            match_score=55,
            match_reason="部分匹配",
            resume_advice=["补充缓存项目经验"],
            risks=["JD 信息较少"],
        ),
        JobItem(
            id="job_high",
            company="示例科技",
            title="Java 后端实习生",
            location="上海",
            source_url="https://jobs.example.com/java",
            source_title="示例科技 Java 后端实习生招聘",
            requirements=["Spring Boot", "MySQL", "Java"],
            responsibilities=["参与后端接口开发"],
            tech_stack=["Java", "Redis"],
            duration="2026 暑期",
            deadline="未确认",
            match_score=86,
            match_reason="城市和技术栈匹配",
            resume_advice=["突出 Spring Boot 项目"],
            risks=["截止日期未确认"],
        ),
    ]
    state.search_diagnostics = [
        {
            "counts": {"raw": 2, "reliable": 1, "filtered": 1},
            "reject_reasons": {"interview_noise": 1},
            "suggestion": "可靠岗位较少，建议补充公司或城市关键词。",
        }
    ]
    return state


class ReportingServiceTests(unittest.TestCase):
    def assert_action_report_sections(self, report: str) -> None:
        self.assertTrue(report.startswith("# 找实习行动报告"))
        self.assertIn("## 1. 结论：今天优先投递", report)
        self.assertIn("## 2. 推荐理由", report)
        self.assertIn("## 3. 简历修改清单", report)
        self.assertIn("## 4. 7 天投递计划", report)
        self.assertIn("## 5. 风险与待确认项", report)
        self.assertIn("## 6. 附录：来源与搜索诊断", report)

    def test_llm_failure_returns_fallback_report(self) -> None:
        agent = FakeReportAgent(exc=RuntimeError("timeout"))
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state_with_jobs())

        self.assert_action_report_sections(report)
        self.assertIn("示例科技", report)
        self.assertIn("https://jobs.example.com/java", report)
        self.assertIn("城市和技术栈匹配", report)
        self.assertIn("突出 Spring Boot 项目", report)
        self.assertIn("今天：", report)
        self.assertIn("3 天内", report)
        self.assertIn("7 天内", report)
        self.assertIn("截止日期未确认", report)
        self.assertIn("可靠来源：1", report)
        self.assertIn("面经/面试 × 1", report)
        self.assertNotIn("后端兜底模板", report)
        self.assertIn("岗位搜索", report)
        self.assertTrue(agent.cleared)

    def test_fallback_report_ranks_jobs_by_match_score(self) -> None:
        agent = FakeReportAgent(response="")
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state_with_jobs())

        self.assertLess(report.index("示例科技"), report.index("低分科技"))

    def test_empty_llm_response_returns_fallback_report(self) -> None:
        agent = FakeReportAgent(response="")
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state())

        self.assert_action_report_sections(report)
        self.assertNotIn("报告生成失败", report)
        self.assertIn("暂无可靠岗位/JD链接", report)

    def test_fallback_without_jobs_does_not_fabricate_job_details(self) -> None:
        agent = FakeReportAgent(exc=RuntimeError("timeout"))
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state())

        self.assert_action_report_sections(report)
        self.assertIn("暂无可靠岗位/JD链接", report)
        self.assertIn("暂无可靠信息", report)
        self.assertNotIn("示例科技", report)
        self.assertNotIn("https://jobs.example.com/java", report)

    def test_long_task_material_is_truncated_before_prompt(self) -> None:
        state = make_state()
        state.todo_items[0].summary = "x" * 3000
        agent = FakeReportAgent(response="# 找实习行动报告\n\nOK")
        service = ReportingService(agent, test_config())

        report = service.generate_report(state)

        self.assertTrue(report.startswith("# 找实习行动报告"))
        self.assertIn("[已截断，保留关键摘要]", agent.prompt)
        self.assertIn("结论：今天优先投递", agent.prompt)
        self.assertLess(len(agent.prompt), 2600)

    def test_llm_report_missing_action_sections_uses_fallback(self) -> None:
        agent = FakeReportAgent(response="# 找实习行动报告\n\nOK")
        service = ReportingService(agent, test_config())

        report = service.generate_report(make_state_with_jobs())

        self.assert_action_report_sections(report)
        self.assertIn("示例科技", report)


if __name__ == "__main__":
    unittest.main()
