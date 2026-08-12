from __future__ import annotations

from backend.events import event_logger
from backend.memory.base import memory_store
from backend.models import AgentProfile, AgentRequest, AgentResponse


class BaseAgent:
    """Common platform contract for all agents."""

    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile

    @property
    def agent_id(self) -> str:
        return self.profile.agent_id

    def run(self, request: AgentRequest) -> AgentResponse:
        event_logger.emit("agent_started", agent_id=self.agent_id, task_id=request.task_id)
        output = self._run(request)
        memory_store.add(self.agent_id, f"input={request.input} output={output}")
        event = event_logger.emit(
            "agent_completed",
            agent_id=self.agent_id,
            task_id=request.task_id,
            payload={"output_preview": output[:200]},
        )
        return AgentResponse(agent_id=self.agent_id, output=output, events=[event])

    def _run(self, request: AgentRequest) -> str:
        raise NotImplementedError
