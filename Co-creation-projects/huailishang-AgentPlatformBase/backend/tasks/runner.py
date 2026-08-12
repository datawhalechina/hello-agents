from __future__ import annotations

from threading import Thread
from time import perf_counter

from backend.agents.registry import AgentRegistry
from backend.events import event_logger
from backend.models import AgentRequest, TaskRecord, TaskStatus
from backend.tasks.manager import TaskManager


class TaskRunner:
    def __init__(self, registry: AgentRegistry, manager: TaskManager) -> None:
        self.registry = registry
        self.manager = manager

    def run(self, task_id: str) -> TaskRecord:
        return self._run_now(task_id)

    def start_background(self, task_id: str) -> TaskRecord:
        task = self.manager.get(task_id)
        if task.status == TaskStatus.running:
            return task
        task = self.manager.update_status(task_id, TaskStatus.running)
        thread = Thread(target=self._run_now, args=(task_id,), daemon=True)
        thread.start()
        return task

    def _run_now(self, task_id: str) -> TaskRecord:
        task = self.manager.update_status(task_id, TaskStatus.running)
        event_logger.emit("task_started", agent_id=task.agent_id, task_id=task_id)
        started = perf_counter()
        try:
            agent = self.registry.get(task.agent_id)
            response = agent.run(AgentRequest(input=task.input, context=task.metadata, task_id=task_id))
            elapsed = round(perf_counter() - started, 3)
            artifacts = dict(response.artifacts)
            artifacts["elapsed_seconds"] = elapsed
            task = self.manager.complete(task_id, output=response.output, artifacts=artifacts)
            event_logger.emit(
                "task_completed",
                agent_id=task.agent_id,
                task_id=task_id,
                payload={"elapsed_seconds": elapsed},
            )
            return task
        except Exception as exc:
            elapsed = round(perf_counter() - started, 3)
            task = self.manager.fail(task_id, str(exc))
            event_logger.emit(
                "task_failed",
                agent_id=task.agent_id,
                task_id=task_id,
                payload={"error": str(exc), "elapsed_seconds": elapsed},
            )
            return task
