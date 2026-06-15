from __future__ import annotations

import json
import os
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
from services.llm_client import (
    CachedLLMClient,
    DryRunLLMClient,
    FakeLLMClient,
    RealLLMClient,
)
from services.run_log import RunLogger


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
    def test_internal_agents_disable_hello_agents_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                for mode in ("fake", "dry_run"):
                    config = Configuration(
                        llm_mode=mode,
                        enable_notes=False,
                        dry_run_skip_search=True,
                        llm_min_interval_seconds=0,
                    )
                    coordinator = DeepResearchAgent(config=config)
                    agents = [
                        coordinator.todo_agent,
                        coordinator.report_agent,
                        coordinator._summarizer_factory(),
                        coordinator._job_extractor_factory(),
                    ]
                    self.assertTrue(
                        all(agent.config.trace_enabled is False for agent in agents)
                    )
                    with patch.object(
                        agent_module,
                        "dispatch_search",
                        side_effect=fake_search_result,
                    ):
                        coordinator.run(f"{mode} Java 后端实习")
            finally:
                os.chdir(original_cwd)

            self.assertFalse((Path(tmpdir) / "memory" / "traces").exists())

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

    def test_fake_mode_applies_configured_cache_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(
                llm_mode="fake",
                llm_cache_mode="read_only",
                llm_cache_dir=str(Path(tmpdir) / "cache"),
                enable_notes=False,
            )

            coordinator = DeepResearchAgent(config=config)

            self.assertIsInstance(coordinator.llm.client, CachedLLMClient)
            self.assertEqual(coordinator.llm.client.mode, "read_only")
            self.assertIsInstance(coordinator.llm.client._wrapped, FakeLLMClient)
            self.assertFalse((Path(tmpdir) / "cache").exists())

    def test_real_mode_applies_configured_cache_mode_without_calling_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(
                llm_mode="real",
                llm_cache_mode="read_only",
                llm_cache_dir=str(Path(tmpdir) / "cache"),
                enable_notes=False,
            )

            llm_stub = type("LLMStub", (), {"model": "stub-model"})()
            with patch.object(agent_module, "HelloAgentsLLM", return_value=llm_stub):
                coordinator = DeepResearchAgent(config=config)

            self.assertIsInstance(coordinator.llm.client, CachedLLMClient)
            self.assertEqual(coordinator.llm.client.mode, "read_only")
            self.assertIsInstance(coordinator.llm.client._wrapped, RealLLMClient)
            self.assertFalse((Path(tmpdir) / "cache").exists())

    def test_dry_run_mode_skips_real_llm_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            config = Configuration(
                llm_mode="dry_run",
                llm_cache_mode="read_write",
                llm_cache_dir=str(cache_dir),
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
                coordinator = DeepResearchAgent(config=config)
                result = coordinator.run("dry-run Java 后端实习")

            self.assertIsInstance(coordinator.llm.client, DryRunLLMClient)
            self.assertFalse(cache_dir.exists())

        self.assertTrue(result.report_markdown.startswith("# 找实习行动报告"))
        self.assertIn("Dry-run 模式", result.report_markdown)
        self.assertTrue(result.search_diagnostics)
        self.assertEqual(result.search_diagnostics[0]["backend"], "dry_run")

    def test_run_log_off_does_not_create_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(
                llm_mode="dry_run",
                llm_run_log_level="off",
                llm_run_log_dir=tmpdir,
                dry_run_skip_search=True,
                enable_notes=False,
                max_agent_steps=1,
                llm_min_interval_seconds=0,
            )

            DeepResearchAgent(config=config).run("private@example.com")

            self.assertEqual(list(Path(tmpdir).glob("run_*.json")), [])

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
            base_config = Configuration(
                llm_mode="fake",
                llm_cache_enabled=True,
                llm_cache_dir=str(Path(tmpdir) / "cache"),
                llm_run_log_level="full",
                enable_notes=False,
                max_agent_steps=1,
                llm_retry_base_delay=0,
                llm_retry_max_delay=0,
                llm_min_interval_seconds=0,
            )
            warmup_config = base_config.model_copy(
                update={"llm_run_log_dir": str(Path(tmpdir) / "warmup")}
            )
            source_config = base_config.model_copy(
                update={"llm_run_log_dir": str(Path(tmpdir) / "source")}
            )
            with patch.object(agent_module, "dispatch_search", side_effect=fake_search_result):
                DeepResearchAgent(config=warmup_config).run("replay Java 后端实习")
                source_result = DeepResearchAgent(config=source_config).run("replay Java 后端实习")

            logs = list((Path(tmpdir) / "source").glob("run_*.json"))
            self.assertEqual(len(logs), 1)
            source_log = json.loads(logs[0].read_text(encoding="utf-8"))
            self.assertEqual(source_log["schema_version"], 3)
            self.assertEqual(source_log["log_level"], "full")
            self.assertTrue(source_log["llm_response"])
            self.assertTrue(
                all(
                    item.get("metadata", {}).get("cache_hit")
                    for item in source_log["llm_response"]
                )
            )

            replay_config = Configuration(
                llm_mode="replay",
                llm_cache_mode="read_write",
                llm_cache_dir=str(Path(tmpdir) / "replay-cache"),
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

            self.assertFalse((Path(tmpdir) / "replay-cache").exists())

        self.assertEqual(replay_result.report_markdown, source_result.report_markdown)
        self.assertEqual(len(replay_result.job_items), len(source_result.job_items))

    def test_metadata_log_replay_fails_before_real_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="metadata",
                log_dir=tmpdir,
                user_input="private@example.com",
            )
            config = Configuration(
                llm_mode="replay",
                llm_replay_log=str(run_logger.path),
                enable_notes=False,
            )

            with (
                patch.object(
                    agent_module,
                    "HelloAgentsLLM",
                    side_effect=AssertionError("real LLM called"),
                ),
                patch.object(
                    agent_module,
                    "dispatch_search",
                    side_effect=AssertionError("real search called"),
                ),
                self.assertRaisesRegex(ValueError, "LLM_RUN_LOG_LEVEL=full"),
            ):
                DeepResearchAgent(config=config)

    def test_stream_log_records_final_answer_and_step_limit_matches_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_config = Configuration(
                llm_mode="dry_run",
                dry_run_skip_search=True,
                enable_notes=False,
                max_agent_steps=1,
                llm_run_log_dir=str(Path(tmpdir) / "sync"),
                llm_retry_base_delay=0,
                llm_retry_max_delay=0,
                llm_min_interval_seconds=0,
            )
            stream_config = sync_config.model_copy(
                update={"llm_run_log_dir": str(Path(tmpdir) / "stream")}
            )

            sync_result = DeepResearchAgent(config=sync_config).run("Java 后端实习")
            events = list(
                DeepResearchAgent(config=stream_config).run_stream("Java 后端实习")
            )
            stream_log_path = next((Path(tmpdir) / "stream").glob("run_*.json"))
            stream_log = json.loads(stream_log_path.read_text(encoding="utf-8"))

        sync_skipped = [item.id for item in sync_result.todo_items if item.status == "skipped"]
        stream_skipped = [
            event["task_id"]
            for event in events
            if event.get("type") == "task_status" and event.get("status") == "skipped"
        ]
        self.assertEqual(stream_skipped, sync_skipped)
        self.assertEqual(stream_log["log_level"], "metadata")
        self.assertEqual(len(stream_log["final_answer"]["sha256"]), 64)
        self.assertIsNone(stream_log["error"])

    def test_stream_fatal_error_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(
                llm_mode="fake",
                enable_notes=False,
                llm_run_log_dir=tmpdir,
                llm_min_interval_seconds=0,
            )
            agent = DeepResearchAgent(config=config)
            agent.planner.plan_todo_list = lambda _state: (_ for _ in ()).throw(
                RuntimeError("stream planner boom")
            )

            with self.assertRaisesRegex(RuntimeError, "stream planner boom"):
                list(agent.run_stream("private@example.com"))

            log_path = next(Path(tmpdir).glob("run_*.json"))
            raw_log = log_path.read_text(encoding="utf-8")
            payload = json.loads(raw_log)

        self.assertNotIn("private@example.com", raw_log)
        self.assertNotIn("stream planner boom", raw_log)
        self.assertEqual(payload["error"]["type"], "RuntimeError")
        self.assertEqual(len(payload["error"]["sha256"]), 64)
        self.assertIsNone(payload["final_answer"])

    def test_stream_worker_error_is_recorded_but_report_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(
                llm_mode="fake",
                enable_notes=False,
                max_agent_steps=1,
                llm_run_log_dir=tmpdir,
                llm_min_interval_seconds=0,
            )
            agent = DeepResearchAgent(config=config)

            def fail_task(*_args, **_kwargs):
                raise RuntimeError("worker boom")
                yield

            agent._execute_task = fail_task
            events = list(agent.run_stream("Java 后端实习"))
            log_path = next(Path(tmpdir).glob("run_*.json"))
            raw_log = log_path.read_text(encoding="utf-8")
            payload = json.loads(raw_log)

        self.assertTrue(any(event.get("type") == "final_report" for event in events))
        self.assertNotIn("worker boom", raw_log)
        self.assertEqual(payload["error"]["type"], "error")
        self.assertEqual(len(payload["error"]["sha256"]), 64)
        self.assertEqual(len(payload["final_answer"]["sha256"]), 64)

    def test_legacy_replay_tool_input_remains_supported(self) -> None:
        coordinator = object.__new__(DeepResearchAgent)
        coordinator.config = Configuration(llm_mode="replay", llm_replay_strict=True)
        coordinator._replay_tool_cursor = 0
        coordinator._run_logger = None
        coordinator._replay_log_data = {
            "tool_result": [
                {
                    "tool_name": "search",
                    "input": {"query": "legacy query", "loop_count": 0},
                    "result": {"backend": "legacy", "search_result": None},
                }
            ]
        }

        result = coordinator._next_replay_tool_result(
            "search",
            {"query": "legacy query", "loop_count": 0},
        )

        self.assertEqual(result["backend"], "legacy")


if __name__ == "__main__":
    unittest.main()
