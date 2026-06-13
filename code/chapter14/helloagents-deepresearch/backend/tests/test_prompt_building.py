from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import SummaryState, TodoItem
from services.job_extractor import JobExtractionService
from services.planner import PlanningService
from services.reporter import ReportingService
from services.summarizer import SummarizationService


class FakeAgent:
    def run(self, _prompt: str) -> str:
        return ""

    def clear_history(self) -> None:
        pass


def make_state() -> SummaryState:
    return SummaryState(
        research_topic="我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot。"
    )


def make_task() -> TodoItem:
    return TodoItem(
        id=1,
        title="岗位搜索",
        intent="搜索可靠岗位/JD来源",
        query="Java 后端 实习 招聘 JD",
        status="completed",
        summary="发现 Java 后端实习线索。",
        sources_summary="示例岗位 https://www.zhipin.com/job_detail/demo.html",
    )


class PromptBuildingTests(unittest.TestCase):
    def test_planner_prompt_contains_user_need_and_format_contract(self) -> None:
        service = PlanningService(FakeAgent(), Configuration())  # type: ignore[arg-type]

        prompt = service.build_prompt(make_state())

        self.assertIn("2026 暑期 Java 后端实习", prompt)
        self.assertIn('"tasks"', prompt)
        self.assertIn("岗位搜索", prompt)
        self.assertIn("不要返回空数组", prompt)

    def test_summarizer_prompt_contains_task_context_and_safety(self) -> None:
        service = SummarizationService(lambda: FakeAgent(), Configuration())  # type: ignore[arg-type]

        prompt = service.build_prompt(
            make_state(),
            make_task(),
            "标题：Java 后端实习\nURL：https://www.zhipin.com/job_detail/demo.html",
        )

        self.assertIn("<用户需求>", prompt)
        self.assertIn("搜索可靠岗位/JD来源", prompt)
        self.assertIn("https://www.zhipin.com/job_detail/demo.html", prompt)
        self.assertIn("不要编造岗位", prompt)
        self.assertIn("保留可追溯来源线索", prompt)

    def test_job_extractor_prompt_contains_json_contract_and_no_fabrication_rule(self) -> None:
        service = JobExtractionService(lambda: FakeAgent(), Configuration())  # type: ignore[arg-type]

        prompt = service.build_prompt(make_state(), make_task(), "岗位详情页上下文")

        self.assertIn("<用户求职目标>", prompt)
        self.assertIn("岗位详情页上下文", prompt)
        self.assertIn("jobs 数组", prompt)
        self.assertIn("match_score", prompt)
        self.assertIn("不要编造岗位、公司、城市、截止日期、薪资或链接", prompt)

    def test_reporter_prompt_contains_action_sections_and_boundaries(self) -> None:
        service = ReportingService(FakeAgent(), Configuration())  # type: ignore[arg-type]
        state = make_state()
        state.todo_items = [make_task()]

        prompt = service.build_prompt(state)

        self.assertIn("# 找实习行动报告", prompt)
        self.assertIn("今天优先投递", prompt)
        self.assertIn("7 天投递计划", prompt)
        self.assertIn("示例岗位 https://www.zhipin.com/job_detail/demo.html", prompt)
        self.assertIn("不要生成自动投递、平台登录、批量联系 HR 或绕过平台规则的建议", prompt)


if __name__ == "__main__":
    unittest.main()
