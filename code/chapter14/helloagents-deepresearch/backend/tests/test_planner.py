from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from models import SummaryState
from services.planner import PlanningService


class FakePlannerAgent:
    def __init__(self, response: str, exc: Exception | None = None) -> None:
        self.response = response
        self.exc = exc
        self.cleared = False

    def run(self, prompt: str) -> str:
        if self.exc:
            raise self.exc
        return self.response

    def clear_history(self) -> None:
        self.cleared = True


def make_service(response: str, exc: Exception | None = None) -> PlanningService:
    return PlanningService(
        FakePlannerAgent(response, exc),  # type: ignore[arg-type]
        Configuration(
            strip_thinking_tokens=True,
            llm_retry_base_delay=0,
            llm_retry_max_delay=0,
            llm_min_interval_seconds=0,
        ),
    )


class PlanningServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = SummaryState(
            research_topic="我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。"
        )

    def test_valid_four_task_json(self) -> None:
        payload = {
            "tasks": [
                {"title": "岗位搜索", "intent": "找岗位", "query": "Java 后端 实习 上海 杭州"},
                {"title": "JD要求分析", "intent": "看要求", "query": "Java 后端 实习 JD Spring Boot"},
                {"title": "投递渠道梳理", "intent": "找渠道", "query": "Java 后端 实习 内推 校招"},
                {"title": "简历优化建议", "intent": "改简历", "query": "Java 后端 实习 简历 项目"},
            ]
        }

        tasks = make_service(json.dumps(payload, ensure_ascii=False)).plan_todo_list(self.state)

        self.assertEqual(len(tasks), 4)
        self.assertEqual([task.title for task in tasks], ["岗位搜索", "JD要求分析", "投递渠道梳理", "简历优化建议"])
        self.assertTrue(all(task.title and task.intent and task.query for task in tasks))
        self.assertIn("BOSS直聘", tasks[0].query)
        self.assertIn("招聘JD", tasks[1].query)

    def test_unparseable_output_falls_back_to_four_tasks(self) -> None:
        tasks = make_service("not json").plan_todo_list(self.state)

        self.assertEqual(len(tasks), 4)
        self.assertEqual([task.title for task in tasks], ["岗位搜索", "JD要求分析", "投递渠道梳理", "简历优化建议"])
        self.assertTrue(all(self.state.research_topic in task.query for task in tasks))

    def test_rate_limit_failure_falls_back_to_four_tasks(self) -> None:
        tasks = make_service(
            "",
            RuntimeError("OpenAI API流式调用失败: Error code: 429 code 1302"),
        ).plan_todo_list(self.state)

        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[0].title, "岗位搜索")
        self.assertTrue(all(task.title and task.intent and task.query for task in tasks))

    def test_short_output_is_padded_to_at_least_three_tasks(self) -> None:
        payload = {
            "tasks": [
                {"title": "岗位搜索", "intent": "找岗位", "query": "Java 后端 实习"},
                {"title": "JD要求分析", "intent": "看要求", "query": "Java 后端 JD"},
            ]
        }

        tasks = make_service(json.dumps(payload, ensure_ascii=False)).plan_todo_list(self.state)

        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[2].title, "投递渠道梳理")
        self.assertTrue(all(task.title and task.intent and task.query for task in tasks))

    def test_long_output_is_truncated_to_five_tasks(self) -> None:
        payload = {
            "tasks": [
                {"title": f"任务{i}", "intent": f"意图{i}", "query": f"查询{i}"}
                for i in range(1, 7)
            ]
        }

        tasks = make_service(json.dumps(payload, ensure_ascii=False)).plan_todo_list(self.state)

        self.assertEqual(len(tasks), 5)
        self.assertEqual(tasks[-1].title, "任务5")
        self.assertTrue(all(task.title and task.intent and task.query for task in tasks))

    def test_missing_fields_are_filled(self) -> None:
        payload = {"tasks": [{"title": "", "intent": "", "query": ""}]}

        tasks = make_service(json.dumps(payload, ensure_ascii=False)).plan_todo_list(self.state)

        self.assertGreaterEqual(len(tasks), 3)
        self.assertTrue(all(task.title and task.intent and task.query for task in tasks))
        self.assertIn(self.state.research_topic, tasks[0].query)


if __name__ == "__main__":
    unittest.main()
