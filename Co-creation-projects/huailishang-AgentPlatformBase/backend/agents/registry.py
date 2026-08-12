from __future__ import annotations

from typing import Dict, Iterable, List

from backend.agents.base import BaseAgent
from backend.agents.profiles import default_profiles
from backend.agents.adapters.deep_research import DeepResearchAdapter
from backend.agents.adapters.rss_digest import RSSDigestAdapter
from backend.models import AgentProfile


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent:
        return self._agents[agent_id]

    def list_profiles(self) -> List[AgentProfile]:
        return [agent.profile for agent in self._agents.values()]

    def ids(self) -> Iterable[str]:
        return self._agents.keys()


def build_default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    profiles = {profile.agent_id: profile for profile in default_profiles()}
    registry.register(DeepResearchAdapter(profiles["deep_research"]))
    registry.register(RSSDigestAdapter(profiles["rss_digest"]))
    return registry
