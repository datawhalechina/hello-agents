from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import agent as agent_module
from agent import DeepResearchAgent
from config import Configuration
from models import TodoItem


def fake_search_result(_query, _config, _loop_count):
    return (
        {
            "results": [
                {
                    "title": "示例科技 Java 后端实习生招聘",
                    "url": "https://www.zhipin.com/job_detail/fake.html",
                    "content": "岗位职责 任职要求 投递 Spring Boot MySQL",
                }
            ],
            "backend": "fake-search",
            "answer": None,
            "notices": [],
        },
        [],
        None,
        "fake-search",
    )


class FakeLLMRuntimeTests(unittest.TestCase):
    def test_fake_mode_runs_without_real_llm_initialization(self) -> None:
        config = Configuration(
            llm_mode="fake",
            enable_notes=False,
            llm_retry_base_delay=0,
            llm_retry_max_delay=0,
            llm_min_interval_seconds=0,
        )

        with (
            patch.object(agent_module, "HelloAgentsLLM", side_effect=AssertionError("real LLM called")),
            patch.object(agent_module, "dispatch_search", side_effect=fake_search_result),
        ):
            result = DeepResearchAgent(config=config).run(
                "我想找 2026 暑期 Java 后端实习，城市上海/杭州。"
            )

        self.assertTrue(result.report_markdown.startswith("# 找实习行动报告"))
        self.assertEqual(len(result.todo_items), 3)
        self.assertTrue(result.job_items)
        self.assertEqual(result.job_items[0].company, "示例科技")

    def test_dry_run_mode_skips_real_llm_and_search(self) -> None:
        config = Configuration(
            llm_mode="dry_run",
            enable_notes=False,
            dry_run_skip_search=True,
            llm_retry_base_delay=0,
            llm_retry_max_delay=0,
            llm_min_interval_seconds=0,
        )

        with (
            patch.object(agent_module, "HelloAgentsLLM", side_effect=AssertionError("real LLM called")),
            patch.object(agent_module, "dispatch_search", side_effect=AssertionError("real search called")),
        ):
            result = DeepResearchAgent(config=config).run("dry-run Java 后端实习")

        self.assertTrue(result.report_markdown.startswith("# 找实习行动报告"))
        self.assertIn("Dry-run 模式", result.report_markdown)
        self.assertTrue(result.search_diagnostics)
        self.assertEqual(result.search_diagnostics[0]["backend"], "dry_run")

    def test_max_agent_steps_marks_extra_tasks_skipped(self) -> None:
        coordinator = object.__new__(DeepResearchAgent)
        coordinator.config = Configuration(max_agent_steps=2)
        tasks = [
            TodoItem(id=1, title="任务1", intent="i", query="q"),
            TodoItem(id=2, title="任务2", intent="i", query="q"),
            TodoItem(id=3, title="任务3", intent="i", query="q"),
        ]

        executable, skipped = coordinator._split_tasks_by_step_limit(tasks)

        self.assertEqual([task.id for task in executable], [1, 2])
        self.assertEqual([task.id for task in skipped], [3])
        self.assertEqual(tasks[2].status, "skipped")
        self.assertIn("MAX_AGENT_STEPS=2", tasks[2].summary or "")

    def test_replay_mode_uses_log_without_real_llm_or_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_config = Configuration(
                llm_mode="fake",
                enable_notes=False,
                max_agent_steps=1,
                llm_run_log_dir=tmpdir,
                llm_retry_base_delay=0,
                llm_retry_max_delay=0,
                llm_min_interval_seconds=0,
            )
            with patch.object(agent_module, "dispatch_search", side_effect=fake_search_result):
                source_result = DeepResearchAgent(config=source_config).run("replay Java 后端实习")

            logs = list(Path(tmpdir).glob("run_*.json"))
            self.assertEqual(len(logs), 1)

            replay_config = Configuration(
                llm_mode="replay",
                llm_replay_log=str(logs[0]),
                llm_replay_strict=True,
                enable_notes=False,
                max_agent_steps=1,
                llm_run_log_dir=str(Path(tmpdir) / "replayed"),
                llm_retry_base_delay=0,
                llm_retry_max_delay=0,
                llm_min_interval_seconds=0,
            )
            with (
                patch.object(agent_module, "HelloAgentsLLM", side_effect=AssertionError("real LLM called")),
                patch.object(agent_module, "dispatch_search", side_effect=AssertionError("real search called")),
            ):
                replay_result = DeepResearchAgent(config=replay_config).run("replay Java 后端实习")

        self.assertEqual(replay_result.report_markdown, source_result.report_markdown)
        self.assertEqual(len(replay_result.job_items), len(source_result.job_items))


if __name__ == "__main__":
    unittest.main()
