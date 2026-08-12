from __future__ import annotations

import importlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from backend.agents.base import BaseAgent
from backend.config import ENV_FILE, ROOT_DIR, settings
from backend.events import event_logger
from backend.maintenance import cleanup_deep_research_artifacts
from backend.memory.base import memory_store
from backend.models import AgentRequest, AgentResponse


class DeepResearchAdapter(BaseAgent):
    """Expose the built-in DeepResearchAgent as one platform-level agent."""

    def run(self, request: AgentRequest) -> AgentResponse:
        event_logger.emit("agent_started", agent_id=self.agent_id, task_id=request.task_id)
        try:
            output, artifacts = self._run_with_artifacts(request)
        except Exception as exc:
            output = f"deep_research 运行失败：{type(exc).__name__}: {exc}"
            artifacts = {"error": str(exc), "error_type": type(exc).__name__}

        memory_store.add(self.agent_id, f"input={request.input} output={output}")
        event = event_logger.emit(
            "agent_completed",
            agent_id=self.agent_id,
            task_id=request.task_id,
            payload={
                "output_preview": output[:200],
                "artifact_keys": sorted(artifacts.keys()),
            },
        )
        return AgentResponse(
            agent_id=self.agent_id,
            output=output,
            artifacts=artifacts,
            events=[event],
        )

    def _run(self, request: AgentRequest) -> str:
        output, _ = self._run_with_artifacts(request)
        return output

    def _run_with_artifacts(self, request: AgentRequest) -> tuple[str, dict[str, Any]]:
        total_started = perf_counter()
        stdout_buffer = io.StringIO()
        timings: dict[str, float] = {}

        cleanup_started = perf_counter()
        cleanup_stats = cleanup_deep_research_artifacts()
        timings["cleanup_seconds"] = round(perf_counter() - cleanup_started, 3)

        if request.context.get("mode") == "group_chat":
            return (
                "deep_research 是长耗时研究流程。请单独使用 @deep_research 提交明确研究主题。",
                {"skipped": True, "reason": "batch_guard", "cleanup": cleanup_stats},
            )

        deep_research_path = Path(settings.chapter14_backend_path).resolve()
        if not deep_research_path.exists():
            return (
                f"DeepResearch 内置源码路径不存在，无法运行 deep_research：{deep_research_path}",
                {
                    "ready": False,
                    "deep_research_path": str(deep_research_path),
                    "cleanup": cleanup_stats,
                },
            )

        if request.context.get("dry_run"):
            return (
                "deep_research 已接入内置 DeepResearchAgent，真实运行时会执行搜索调研流程。",
                {
                    "ready": True,
                    "deep_research_path": str(deep_research_path),
                    "cleanup": cleanup_stats,
                },
            )

        topic_preview = request.input.replace("\n", " ")[:120]
        print(f"[deep_research] start task_id={request.task_id or '-'} topic={topic_preview}")

        started = perf_counter()
        with redirect_stdout(stdout_buffer):
            DeepResearchAgent, Configuration = self._load_deep_research_types(deep_research_path)
        timings["load_deep_research_seconds"] = round(perf_counter() - started, 3)
        print(f"[deep_research] loaded source={deep_research_path}")

        started = perf_counter()
        with redirect_stdout(stdout_buffer):
            config = Configuration.from_env(overrides=self._deep_research_overrides())
            agent = DeepResearchAgent(config=config)
        timings["agent_init_seconds"] = round(perf_counter() - started, 3)
        print(
            "[deep_research] initialized "
            f"search={config.search_api.value if hasattr(config.search_api, 'value') else config.search_api} "
            f"model={config.resolved_model() or '-'}"
        )

        started = perf_counter()
        print("[deep_research] researching...")
        with redirect_stdout(stdout_buffer):
            result = agent.run(request.input)
        timings["agent_run_seconds"] = round(perf_counter() - started, 3)

        started = perf_counter()
        todo_items = [self._serialize_todo(item) for item in result.todo_items]
        report = (result.report_markdown or result.running_summary or "").strip()
        completed_items = [
            item for item in todo_items if item.get("status") == "completed" and item.get("summary")
        ]
        skipped_items = [item for item in todo_items if item.get("status") == "skipped"]
        failed_items = [item for item in todo_items if item.get("status") == "failed"]
        artifacts: dict[str, Any] = {
            "report_markdown": report,
            "todo_items": todo_items,
            "cleanup": cleanup_stats,
        }
        captured_stdout = stdout_buffer.getvalue().strip()
        if captured_stdout:
            artifacts["stdout"] = captured_stdout
        timings["postprocess_seconds"] = round(perf_counter() - started, 3)
        timings["total_seconds"] = round(perf_counter() - total_started, 3)
        artifacts["timings"] = timings
        if todo_items:
            artifacts["todo_count"] = len(todo_items)
            artifacts["completed_count"] = len(completed_items)
            artifacts["skipped_count"] = len(skipped_items)
            artifacts["failed_count"] = len(failed_items)

        print(
            "[deep_research] research completed "
            f"tasks={len(todo_items)} completed={len(completed_items)} "
            f"skipped={len(skipped_items)} failed={len(failed_items)}"
        )
        print(f"[deep_research] report generated chars={len(report)}")

        if todo_items and not completed_items and not report:
            output = (
                "搜索员没有拿到可用的搜索总结，因此未返回正式研究报告。\n"
                "可能原因：搜索后端无结果、网络 API 调用失败，或任务执行阶段没有产出摘要。\n"
                "请查看后端日志和 data/deep_research/runs 目录下的 task_* 文件。"
            )
            print(f"[deep_research] failed seconds={timings['total_seconds']}")
            return output, artifacts

        if todo_items and not completed_items:
            artifacts["warning"] = "no_completed_research_tasks"

        output = report or "deep_research 已完成，但没有生成报告正文。"
        print(f"[deep_research] complete seconds={timings['total_seconds']}")
        return output, artifacts

    def _load_deep_research_types(self, deep_research_path: Path) -> tuple[type[Any], type[Any]]:
        path_text = str(deep_research_path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

        agent_module = importlib.import_module("agent")
        config_module = importlib.import_module("config")
        if ENV_FILE.exists():
            load_dotenv(ENV_FILE, override=True)

        return agent_module.DeepResearchAgent, config_module.Configuration

    def _deep_research_overrides(self) -> dict[str, Any]:
        overrides: dict[str, Any] = {
            "notes_workspace": self._resolve_workspace(settings.notes_workspace),
            "run_workspace": self._resolve_workspace(settings.run_workspace),
        }

        optional_values = {
            "llm_provider": settings.llm_provider,
            "llm_model_id": settings.llm_model_id,
            "llm_api_key": settings.llm_api_key,
            "llm_base_url": settings.llm_base_url,
            "llm_timeout": settings.llm_timeout,
            "search_api": settings.search_api,
            "max_web_research_loops": settings.max_web_research_loops,
            "fetch_full_page": settings.fetch_full_page,
            "enable_notes": settings.enable_notes,
            "persist_runs": settings.persist_runs,
            "cleanup_intermediate_files": settings.cleanup_intermediate_files,
        }
        for key, value in optional_values.items():
            if value is not None:
                overrides[key] = value

        return overrides

    @staticmethod
    def _resolve_workspace(value: str) -> str:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @staticmethod
    def _serialize_todo(item: Any) -> dict[str, Any]:
        return {
            "id": getattr(item, "id", None),
            "title": getattr(item, "title", ""),
            "intent": getattr(item, "intent", ""),
            "query": getattr(item, "query", ""),
            "status": getattr(item, "status", ""),
            "summary": getattr(item, "summary", None),
            "sources_summary": getattr(item, "sources_summary", None),
            "note_id": getattr(item, "note_id", None),
            "note_path": getattr(item, "note_path", None),
        }
