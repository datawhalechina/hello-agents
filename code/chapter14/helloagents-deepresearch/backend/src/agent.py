"""Orchestrator coordinating the deep research workflow."""

from __future__ import annotations

import logging
import io
import re
from contextlib import redirect_stdout
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Semaphore, Thread
from typing import Any, Callable, Iterator
from uuid import uuid4

from hello_agents import HelloAgentsLLM
from hello_agents.tools import ToolRegistry

from config import Configuration
from note_tool import NoteTool
from tool_aware_agent import ToolAwareSimpleAgent
from prompts import (
    job_extractor_instructions,
    report_writer_instructions,
    task_summarizer_instructions,
    todo_planner_system_prompt,
)
from models import JobItem, SummaryState, SummaryStateOutput, TodoItem
from services.job_extractor import JobExtractionService
from services.planner import PlanningService
from services.reporter import ReportingService
from services.search import (
    build_platform_job_query,
    build_search_diagnostics,
    build_strict_job_query,
    dispatch_search,
    merge_search_results,
    prepare_research_context,
    prioritize_job_search_results,
)
from services.search_diagnostics import persist_search_diagnostics
from services.summarizer import SummarizationService
from services.tool_events import ToolCallTracker
from services.llm_client import (
    CachedLLMClient,
    DryRunLLMClient,
    FakeLLMClient,
    HelloAgentsCompatibleLLM,
    RealLLMClient,
    ReplayLLMClient,
)
from services.run_log import (
    RunLogger,
    load_run_log,
    summarize_sensitive_payload,
)

logger = logging.getLogger(__name__)


class DeepResearchAgent:
    """Coordinator orchestrating TODO-based research workflow using HelloAgents."""

    def __init__(self, config: Configuration | None = None) -> None:
        """Initialise the coordinator with configuration and shared tools."""
        self.config = config or Configuration.from_env()
        self._run_logger: RunLogger | None = None
        self._replay_log_data = self._load_replay_log_data()
        self._replay_tool_cursor = 0
        self.llm = self._init_llm()

        self.note_tool = (
            NoteTool(workspace=self.config.notes_workspace)
            if self.config.enable_notes
            else None
        )
        self.tools_registry: ToolRegistry | None = None
        if self.note_tool:
            registry = ToolRegistry()
            with redirect_stdout(io.StringIO()):
                registry.register_tool(self.note_tool)
            self.tools_registry = registry

        self._tool_tracker = ToolCallTracker(
            self.config.notes_workspace if self.config.enable_notes else None
        )
        self._tool_event_sink_enabled = False
        self._state_lock = Lock()

        self.todo_agent = self._create_tool_aware_agent(
            name="求职规划专家",
            system_prompt=todo_planner_system_prompt.strip(),
        )
        self.report_agent = self._create_tool_aware_agent(
            name="求职行动报告专家",
            system_prompt=report_writer_instructions.strip(),
        )

        self._summarizer_factory: Callable[[], ToolAwareSimpleAgent] = lambda: self._create_tool_aware_agent(  # noqa: E501
            name="岗位分析专家",
            system_prompt=task_summarizer_instructions.strip(),
        )
        self._job_extractor_factory: Callable[[], ToolAwareSimpleAgent] = lambda: self._create_tool_aware_agent(  # noqa: E501
            name="岗位抽取与匹配专家",
            system_prompt=job_extractor_instructions.strip(),
        )

        self.planner = PlanningService(self.todo_agent, self.config)
        self.summarizer = SummarizationService(self._summarizer_factory, self.config)
        self.job_extractor = JobExtractionService(
            self._job_extractor_factory,
            self.config,
        )
        self.reporting = ReportingService(self.report_agent, self.config)
        self._last_search_notices: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _init_llm(self) -> HelloAgentsCompatibleLLM:
        """Instantiate the shared LLM adapter following configuration preferences."""
        mode = (self.config.llm_mode or "real").strip().lower()
        if mode == "fake":
            client = FakeLLMClient()
            if self.config.llm_cache_enabled:
                client = CachedLLMClient(client, self.config.llm_cache_dir)
            return HelloAgentsCompatibleLLM(
                client,
                model="fake-llm",
                temperature=0.0,
            )
        if mode == "dry_run":
            return HelloAgentsCompatibleLLM(
                DryRunLLMClient(),
                model="dry-run-llm",
                temperature=0.0,
            )
        if mode == "replay":
            return HelloAgentsCompatibleLLM(
                ReplayLLMClient(
                    self.config.llm_replay_log or "",
                    strict=self.config.llm_replay_strict,
                ),
                model="replay-llm",
                temperature=0.0,
            )

        llm_kwargs: dict[str, Any] = {
            "temperature": 0.0,
            "timeout": self.config.llm_timeout,
        }

        model_id = self.config.llm_model_id or self.config.local_llm
        if model_id:
            llm_kwargs["model"] = model_id

        provider = (self.config.llm_provider or "").strip()
        if provider:
            llm_kwargs["provider"] = provider

        if provider == "ollama":
            llm_kwargs["base_url"] = self.config.sanitized_ollama_url()
            if self.config.llm_api_key:
                llm_kwargs["api_key"] = self.config.llm_api_key
            else:
                llm_kwargs["api_key"] = "ollama"
        elif provider == "lmstudio":
            llm_kwargs["base_url"] = self.config.lmstudio_base_url
            if self.config.llm_api_key:
                llm_kwargs["api_key"] = self.config.llm_api_key
        else:
            if self.config.llm_base_url:
                llm_kwargs["base_url"] = self.config.llm_base_url
            if self.config.llm_api_key:
                llm_kwargs["api_key"] = self.config.llm_api_key

        real_llm = HelloAgentsLLM(**llm_kwargs)
        client = RealLLMClient(real_llm)
        if self.config.llm_cache_enabled:
            client = CachedLLMClient(client, self.config.llm_cache_dir)
        return HelloAgentsCompatibleLLM(
            client,
            model=model_id or self.config.resolved_model() or "unknown",
            temperature=0.0,
        )

    def _create_tool_aware_agent(self, *, name: str, system_prompt: str) -> ToolAwareSimpleAgent:
        """Instantiate a ToolAwareSimpleAgent sharing tool registry and tracker."""
        return ToolAwareSimpleAgent(
            name=name,
            llm=self.llm,
            system_prompt=system_prompt,
            enable_tool_calling=self.tools_registry is not None,
            tool_registry=self.tools_registry,
            tool_call_listener=self._tool_tracker.record,
        )

    def _set_tool_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        """Enable or disable immediate tool event callbacks."""
        self._tool_event_sink_enabled = sink is not None
        self._tool_tracker.set_event_sink(sink)

    def _create_state(self, topic: str) -> SummaryState:
        """Create per-run state with a stable diagnostic run id."""
        return SummaryState(run_id=uuid4().hex[:12], research_topic=topic)

    def _load_replay_log_data(self) -> dict[str, Any] | None:
        if (self.config.llm_mode or "").strip().lower() != "replay":
            return None
        if not self.config.llm_replay_log:
            return None
        return load_run_log(self.config.llm_replay_log)

    def _start_run_logger(self, state: SummaryState, topic: str) -> None:
        self._run_logger = RunLogger(
            run_id=state.run_id or uuid4().hex[:12],
            log_dir=self.config.llm_run_log_dir,
            user_input=topic,
        )
        if hasattr(self.llm, "set_run_logger"):
            self.llm.set_run_logger(self._run_logger)

    def run(self, topic: str) -> SummaryStateOutput:
        """Execute the research workflow and return the final report."""
        state = self._create_state(topic)
        self._start_run_logger(state, topic)
        try:
            state.todo_items = self.planner.plan_todo_list(state)
            self._drain_tool_events(state)

            if not state.todo_items:
                logger.info("No TODO items generated; falling back to internship tasks")
                state.todo_items = self.planner.create_fallback_tasks(state)

            executable_tasks, _skipped_tasks = self._split_tasks_by_step_limit(state.todo_items)
            for task in executable_tasks:
                for _ in self._execute_task(state, task, emit_stream=False):
                    pass

            report = self.reporting.generate_report(state)
            self._drain_tool_events(state)
            state.structured_report = report
            state.running_summary = report
            if self._run_logger:
                self._run_logger.set_final_answer(report)
            try:
                self._persist_final_report(state, report)
            except Exception as exc:  # pragma: no cover - report should still return
                logger.exception("Persisting final report note failed", exc_info=exc)
            self._persist_search_diagnostics(state)

            return SummaryStateOutput(
                running_summary=report,
                report_markdown=report,
                todo_items=state.todo_items,
                job_items=state.job_items,
                search_diagnostics=state.search_diagnostics,
            )
        except Exception as exc:
            if self._run_logger:
                self._run_logger.set_error(exc)
            raise

    def run_stream(self, topic: str) -> Iterator[dict[str, Any]]:
        """Execute the streaming workflow and persist fatal errors."""

        try:
            yield from self._run_stream_impl(topic)
        except Exception as exc:
            if self._run_logger:
                self._run_logger.set_error(exc)
            raise

    def _run_stream_impl(self, topic: str) -> Iterator[dict[str, Any]]:
        """Execute the workflow yielding incremental progress events."""
        state = self._create_state(topic)
        self._start_run_logger(state, topic)
        logger.debug("Starting streaming research: topic=%s", topic)
        yield {"type": "status", "message": "初始化找实习流程"}

        state.todo_items = self.planner.plan_todo_list(state)
        for event in self._drain_tool_events(state, step=0):
            yield event
        if not state.todo_items:
            state.todo_items = self.planner.create_fallback_tasks(state)

        channel_map: dict[int, dict[str, Any]] = {}
        for index, task in enumerate(state.todo_items, start=1):
            token = f"task_{task.id}"
            task.stream_token = token
            channel_map[task.id] = {"step": index, "token": token}

        executable_tasks, skipped_tasks = self._split_tasks_by_step_limit(state.todo_items)

        yield {
            "type": "todo_list",
            "tasks": [self._serialize_task(t) for t in state.todo_items],
            "step": 0,
        }

        for task in skipped_tasks:
            channel = channel_map.get(task.id, {})
            yield {
                "type": "task_status",
                "task_id": task.id,
                "status": task.status,
                "summary": task.summary,
                "title": task.title,
                "intent": task.intent,
                "note_id": task.note_id,
                "note_path": task.note_path,
                "step": channel.get("step", 0),
                "stream_token": channel.get("token"),
            }

        event_queue: Queue[dict[str, Any]] = Queue()

        def enqueue(
            event: dict[str, Any],
            *,
            task: TodoItem | None = None,
            step_override: int | None = None,
        ) -> None:
            payload = dict(event)
            target_task_id = payload.get("task_id")
            if task is not None:
                target_task_id = task.id
                payload["task_id"] = task.id

            channel = channel_map.get(target_task_id) if target_task_id is not None else None
            if channel:
                payload.setdefault("step", channel["step"])
                payload["stream_token"] = channel["token"]
            if step_override is not None:
                payload["step"] = step_override
            event_queue.put(payload)

        def tool_event_sink(event: dict[str, Any]) -> None:
            enqueue(event)

        self._set_tool_event_sink(tool_event_sink)

        threads: list[Thread] = []
        task_semaphore = Semaphore(max(1, self.config.task_concurrency))

        def worker(task: TodoItem, step: int) -> None:
            try:
                enqueue(
                    {
                        "type": "task_status",
                        "task_id": task.id,
                        "status": "in_progress",
                        "title": task.title,
                        "intent": task.intent,
                        "note_id": task.note_id,
                        "note_path": task.note_path,
                    },
                    task=task,
                )

                with task_semaphore:
                    for event in self._execute_task(state, task, emit_stream=True, step=step):
                        enqueue(event, task=task)
            except Exception as exc:  # pragma: no cover - defensive guardrail
                logger.exception("Task execution failed", exc_info=exc)
                if self._run_logger:
                    self._run_logger.set_error(f"Task {task.id} failed: {exc}")
                enqueue(
                    {
                        "type": "task_status",
                        "task_id": task.id,
                        "status": "failed",
                        "detail": str(exc),
                        "title": task.title,
                        "intent": task.intent,
                        "note_id": task.note_id,
                        "note_path": task.note_path,
                    },
                    task=task,
                )
            finally:
                enqueue({"type": "__task_done__", "task_id": task.id})

        for task in executable_tasks:
            step = channel_map.get(task.id, {}).get("step", 0)
            thread = Thread(target=worker, args=(task, step), daemon=True)
            threads.append(thread)
            thread.start()

        active_workers = len(executable_tasks)
        finished_workers = 0

        try:
            while finished_workers < active_workers:
                event = event_queue.get()
                if event.get("type") == "__task_done__":
                    finished_workers += 1
                    continue
                yield event

            while True:
                try:
                    event = event_queue.get_nowait()
                except Empty:
                    break
                if event.get("type") != "__task_done__":
                    yield event
        finally:
            self._set_tool_event_sink(None)
            for thread in threads:
                thread.join()

        report = self.reporting.generate_report(state)
        final_step = len(state.todo_items) + 1
        for event in self._drain_tool_events(state, step=final_step):
            yield event
        state.structured_report = report
        state.running_summary = report
        if self._run_logger:
            self._run_logger.set_final_answer(report)

        try:
            note_event = self._persist_final_report(state, report)
        except Exception as exc:  # pragma: no cover - report should still stream
            logger.exception("Persisting final report note failed", exc_info=exc)
            note_event = None
        if note_event:
            yield note_event

        self._persist_search_diagnostics(state)

        yield {
            "type": "final_report",
            "report": report,
            "job_items": [self._serialize_job(job) for job in state.job_items],
            "search_diagnostics": state.search_diagnostics,
            "search_diagnostics_path": state.search_diagnostics_path,
            "note_id": state.report_note_id,
            "note_path": state.report_note_path,
        }
        yield {"type": "done"}

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------
    def _split_tasks_by_step_limit(
        self,
        tasks: list[TodoItem],
    ) -> tuple[list[TodoItem], list[TodoItem]]:
        """Apply the configured max task limit for low-cost development runs."""

        max_steps = int(self.config.max_agent_steps)
        if max_steps <= 0 or len(tasks) <= max_steps:
            return tasks, []

        executable = tasks[:max_steps]
        skipped = tasks[max_steps:]
        for task in skipped:
            task.status = "skipped"
            task.summary = (
                f"已达到 MAX_AGENT_STEPS={max_steps}，开发阶段跳过该任务，"
                "避免一次运行触发过多模型调用。"
            )
        return executable, skipped

    def _dispatch_search(
        self,
        query: str,
        loop_count: int,
    ) -> tuple[dict[str, Any] | None, list[str], str | None, str]:
        """Dispatch search or return deterministic dry-run data."""

        if self._is_replay():
            result = self._next_replay_tool_result("search", {"query": query, "loop_count": loop_count})
            return (
                result.get("search_result"),
                list(result.get("notices") or []),
                result.get("answer_text"),
                str(result.get("backend") or "replay"),
            )

        if self._is_dry_run() and self.config.dry_run_skip_search:
            payload = {
                "results": [
                    {
                        "title": "Dry-run 示例科技 Java 后端实习生招聘",
                        "url": "https://www.zhipin.com/job_detail/dry-run.html",
                        "content": (
                            "岗位职责 任职要求 投递入口 Spring Boot MySQL Redis。"
                            "此结果为 dry-run 本地模拟，真实投递前必须点开来源核验。"
                        ),
                        "raw_content": "",
                    }
                ],
                "backend": "dry_run",
                "answer": None,
                "notices": ["dry-run: skipped real search backend"],
            }
            result = (payload, list(payload["notices"]), None, "dry_run")
        else:
            result = dispatch_search(query, self.config, loop_count)

        search_result, notices, answer_text, backend = result
        self._record_tool_result(
            "search",
            {"query": query, "loop_count": loop_count},
            {
                "search_result": search_result,
                "notices": notices,
                "answer_text": answer_text,
                "backend": backend,
            },
        )
        return result

    def _is_dry_run(self) -> bool:
        return (self.config.llm_mode or "").strip().lower() == "dry_run"

    def _is_replay(self) -> bool:
        return (self.config.llm_mode or "").strip().lower() == "replay"

    def _record_tool_result(
        self,
        tool_name: str,
        input_payload: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        run_logger = getattr(self, "_run_logger", None)
        if run_logger:
            run_logger.record_tool_result(
                tool_name=tool_name,
                input_payload=input_payload,
                result=result,
            )

    def _next_replay_tool_result(
        self,
        tool_name: str,
        input_payload: dict[str, Any],
    ) -> dict[str, Any]:
        tool_results = list((self._replay_log_data or {}).get("tool_result") or [])
        while self._replay_tool_cursor < len(tool_results):
            payload = tool_results[self._replay_tool_cursor]
            self._replay_tool_cursor += 1
            if payload.get("tool_name") != tool_name:
                continue
            if self.config.llm_replay_strict:
                expected_input = payload.get("input")
                expected_hash = payload.get("input_hash")
                actual_summary = summarize_sensitive_payload(input_payload)
                input_matches = (
                    expected_hash == actual_summary["sha256"]
                    if expected_hash
                    else expected_input == input_payload
                )
                if not input_matches:
                    expected = expected_hash or expected_input
                    raise RuntimeError(
                        f"Replay tool input mismatch for {tool_name}: "
                        f"expected {expected}, got {actual_summary['sha256']}"
                    )
            result = payload.get("result")
            if isinstance(result, dict):
                self._record_tool_result(tool_name, input_payload, result)
                return result

        raise RuntimeError(f"Replay log has no remaining {tool_name} tool results")

    def _execute_task(
        self,
        state: SummaryState,
        task: TodoItem,
        *,
        emit_stream: bool,
        step: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Run search + summarization for a single task."""
        task.status = "in_progress"

        original_query = task.query
        is_job_search_task = self._is_job_search_task(task)
        if is_job_search_task:
            task.query = build_strict_job_query(task.query)

        search_result, notices, answer_text, backend = self._dispatch_search(
            task.query,
            state.research_loop_count,
        )
        raw_search_results = self._extract_search_results(search_result)
        retry_query: str | None = None

        if is_job_search_task:
            search_result = prioritize_job_search_results(search_result)
            if not search_result or not search_result.get("results"):
                retry_query = build_platform_job_query(original_query)
                retry_result, retry_notices, retry_answer, retry_backend = self._dispatch_search(
                    retry_query,
                    state.research_loop_count,
                )
                raw_search_results.extend(self._extract_search_results(retry_result))
                retry_result = prioritize_job_search_results(retry_result)
                search_result = merge_search_results(search_result, retry_result)
                notices.extend(retry_notices)
                answer_text = answer_text or retry_answer
                backend = retry_backend or backend
                task.query = retry_query

        self._last_search_notices = notices
        task.notices = notices

        if self._is_job_extraction_task(task):
            diagnostics = build_search_diagnostics(
                task_id=task.id,
                task_title=task.title,
                backend=backend,
                query=original_query,
                final_query=task.query,
                retry_query=retry_query,
                raw_results=raw_search_results,
            )
            with self._state_lock:
                state.search_diagnostics.append(diagnostics)
            if emit_stream:
                yield {
                    "type": "search_diagnostics",
                    "task_id": task.id,
                    "diagnostics": diagnostics,
                    "step": step,
                }

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
        else:
            self._drain_tool_events(state)

        if notices and emit_stream:
            for notice in notices:
                if notice:
                    yield {
                        "type": "status",
                        "message": notice,
                        "task_id": task.id,
                        "step": step,
                    }

        if not search_result or not search_result.get("results"):
            task.status = "skipped"
            if emit_stream:
                for event in self._drain_tool_events(state, step=step):
                    yield event
                yield {
                    "type": "task_status",
                    "task_id": task.id,
                    "status": "skipped",
                    "title": task.title,
                    "intent": task.intent,
                    "note_id": task.note_id,
                    "note_path": task.note_path,
                    "step": step,
                }
            else:
                self._drain_tool_events(state)
            return
        else:
            if not emit_stream:
                self._drain_tool_events(state)

        sources_summary, context = prepare_research_context(
            search_result,
            answer_text,
            self.config,
        )

        task.sources_summary = sources_summary

        with self._state_lock:
            state.web_research_results.append(context)
            state.sources_gathered.append(sources_summary)
            state.research_loop_count += 1

        if self._is_job_extraction_task(task):
            jobs = self.job_extractor.extract_jobs(state, task, search_result, context)
            if jobs:
                with self._state_lock:
                    state.job_items = self._merge_job_items(state.job_items, jobs)
                    all_jobs_snapshot = list(state.job_items)
                if emit_stream:
                    yield {
                        "type": "job_items",
                        "task_id": task.id,
                        "jobs": [self._serialize_job(job) for job in jobs],
                        "all_jobs": [
                            self._serialize_job(job) for job in all_jobs_snapshot
                        ],
                        "step": step,
                    }

        summary_text: str | None = None

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
            yield {
                "type": "sources",
                "task_id": task.id,
                "latest_sources": sources_summary,
                "raw_context": context,
                "step": step,
                "backend": backend,
                "note_id": task.note_id,
                "note_path": task.note_path,
            }

            summary_stream, summary_getter = self.summarizer.stream_task_summary(state, task, context)
            try:
                for event in self._drain_tool_events(state, step=step):
                    yield event
                for chunk in summary_stream:
                    if chunk:
                        yield {
                            "type": "task_summary_chunk",
                            "task_id": task.id,
                            "content": chunk,
                            "note_id": task.note_id,
                            "step": step,
                        }
                    for event in self._drain_tool_events(state, step=step):
                        yield event
            finally:
                summary_text = summary_getter()
        else:
            summary_text = self.summarizer.summarize_task(state, task, context)
            self._drain_tool_events(state)

        task.summary = summary_text.strip() if summary_text else "暂无可用信息"
        task.status = "completed"

        if emit_stream:
            for event in self._drain_tool_events(state, step=step):
                yield event
            yield {
                "type": "task_status",
                "task_id": task.id,
                "status": "completed",
                "summary": task.summary,
                "sources_summary": task.sources_summary,
                "note_id": task.note_id,
                "note_path": task.note_path,
                "step": step,
            }
        else:
            self._drain_tool_events(state)

    def _drain_tool_events(
        self,
        state: SummaryState,
        *,
        step: int | None = None,
    ) -> list[dict[str, Any]]:
        """Proxy to the shared tool call tracker."""
        events = self._tool_tracker.drain(state, step=step)
        if self._tool_event_sink_enabled:
            return []
        return events

    @property
    def _tool_call_events(self) -> list[dict[str, Any]]:
        """Expose recorded tool events for legacy integrations."""
        return self._tool_tracker.as_dicts()

    def _persist_search_diagnostics(self, state: SummaryState) -> None:
        """Persist per-run search diagnostics when available."""
        if state.search_diagnostics_path:
            return
        try:
            path = persist_search_diagnostics(
                run_id=state.run_id or uuid4().hex[:12],
                diagnostics=state.search_diagnostics,
            )
        except Exception as exc:  # pragma: no cover - diagnostics should not block report
            logger.exception("Persisting search diagnostics failed", exc_info=exc)
            return
        state.search_diagnostics_path = path

    @staticmethod
    def _extract_search_results(search_result: dict[str, Any] | None) -> list[dict[str, Any]]:
        """Return dict search results from a structured search payload."""
        if not search_result:
            return []
        results = search_result.get("results")
        if not isinstance(results, list):
            return []
        return [item for item in results if isinstance(item, dict)]

    def _serialize_task(self, task: TodoItem) -> dict[str, Any]:
        """Convert task dataclass to serializable dict for frontend."""
        return {
            "id": task.id,
            "title": task.title,
            "intent": task.intent,
            "query": task.query,
            "status": task.status,
            "summary": task.summary,
            "sources_summary": task.sources_summary,
            "note_id": task.note_id,
            "note_path": task.note_path,
            "stream_token": task.stream_token,
        }

    def _serialize_job(self, job: JobItem) -> dict[str, Any]:
        """Convert extracted job dataclass to serializable dict for frontend."""
        return {
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "source_url": job.source_url,
            "source_title": job.source_title,
            "requirements": job.requirements,
            "responsibilities": job.responsibilities,
            "tech_stack": job.tech_stack,
            "duration": job.duration,
            "deadline": job.deadline,
            "match_score": job.match_score,
            "match_reason": job.match_reason,
            "resume_advice": job.resume_advice,
            "risks": job.risks,
        }

    def _merge_job_items(
        self,
        existing: list[JobItem],
        incoming: list[JobItem],
    ) -> list[JobItem]:
        """Merge extracted jobs while preserving unique source URLs."""
        merged: list[JobItem] = []
        seen: set[str] = set()
        for job in [*existing, *incoming]:
            key = self._job_dedupe_key(job)
            if key in seen:
                continue
            seen.add(key)
            merged.append(job)
        return merged

    @staticmethod
    def _job_dedupe_key(job: JobItem) -> str:
        url = (job.source_url or "").strip().lower()
        if url and url != "未确认":
            return f"url:{url}"
        return f"text:{job.company.strip().lower()}|{job.title.strip().lower()}"

    @staticmethod
    def _is_job_search_task(task: TodoItem) -> bool:
        """Return True for tasks whose purpose is finding concrete job/JD links."""

        text = f"{task.title} {task.intent}"
        return "岗位搜索" in text or ("岗位" in text and "搜索" in text)

    @staticmethod
    def _is_job_extraction_task(task: TodoItem) -> bool:
        """Return True for tasks likely to contain concrete jobs or JD details."""

        text = f"{task.title} {task.intent} {task.query}"
        return any(
            keyword in text
            for keyword in (
                "岗位搜索",
                "JD要求",
                "JD分析",
                "招聘JD",
                "岗位要求",
                "职位描述",
                "任职要求",
            )
        )

    def _persist_final_report(self, state: SummaryState, report: str) -> dict[str, Any] | None:
        if not self.note_tool or not report or not report.strip():
            return None

        note_title = f"找实习行动报告：{state.research_topic}".strip() or "找实习行动报告"
        tags = ["internship_agent", "report"]
        content = report.strip()

        note_id = self._find_existing_report_note_id(state)
        response = ""

        if note_id:
            response = self._run_note_tool_text(
                {
                    "action": "update",
                    "note_id": note_id,
                    "title": note_title,
                    "note_type": "conclusion",
                    "tags": tags,
                    "content": content,
                }
            )
            if response.startswith("❌"):
                note_id = None

        if not note_id:
            response = self._run_note_tool_text(
                {
                    "action": "create",
                    "title": note_title,
                    "note_type": "conclusion",
                    "tags": tags,
                    "content": content,
                }
            )
            note_id = self._extract_note_id_from_text(response)

        if not note_id:
            return None

        state.report_note_id = note_id
        if self.config.notes_workspace:
            note_path = Path(self.config.notes_workspace) / f"{note_id}.md"
            state.report_note_path = str(note_path)
        else:
            note_path = None

        payload = {
            "type": "report_note",
            "note_id": note_id,
            "title": note_title,
            "content": content,
        }
        if note_path:
            payload["note_path"] = str(note_path)

        return payload

    def _run_note_tool_text(self, parameters: dict[str, Any]) -> str:
        response = self.note_tool.run(parameters) if self.note_tool else None
        if hasattr(response, "text"):
            return str(response.text)
        return str(response or "")

    def _find_existing_report_note_id(self, state: SummaryState) -> str | None:
        if state.report_note_id:
            return state.report_note_id

        for event in reversed(self._tool_tracker.as_dicts()):
            if event.get("tool") != "note":
                continue

            parameters = event.get("parsed_parameters") or {}
            if not isinstance(parameters, dict):
                continue

            action = parameters.get("action")
            if action not in {"create", "update"}:
                continue

            note_type = parameters.get("note_type")
            if note_type != "conclusion":
                title = parameters.get("title")
                if not (
                    isinstance(title, str)
                    and title.startswith(("研究报告", "找实习行动报告"))
                ):
                    continue

            note_id = parameters.get("note_id")
            if not note_id:
                note_id = self._tool_tracker._extract_note_id(event.get("result", ""))  # type: ignore[attr-defined]

            if note_id:
                return note_id

        return None

    @staticmethod
    def _extract_note_id_from_text(response: str) -> str | None:
        if not response:
            return None

        match = re.search(r"ID:\s*([^\n]+)", response)
        if not match:
            return None

        return match.group(1).strip()


def run_deep_research(topic: str, config: Configuration | None = None) -> SummaryStateOutput:
    """Convenience function mirroring the class-based API."""
    agent = DeepResearchAgent(config=config)
    return agent.run(topic)
