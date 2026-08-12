from __future__ import annotations

from typing import Dict

from backend.agents.registry import AgentRegistry
from backend.models import AgentRequest, AgentResponse


class BatchRunner:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def run(self, requests: Dict[str, AgentRequest]) -> Dict[str, AgentResponse]:
        responses: Dict[str, AgentResponse] = {}
        for agent_id, request in requests.items():
            responses[agent_id] = self.registry.get(agent_id).run(request)
        return responses
