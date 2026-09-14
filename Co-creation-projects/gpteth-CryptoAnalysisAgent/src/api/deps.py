"""Shared runtime: workspace, memory, sessions, chat agent, analysis pipeline."""

from __future__ import annotations

import os
from typing import Any, Optional

from ..memory.store import MemoryStore
from ..session.store import SessionStore
from ..workspace.manager import WorkspaceManager

_workspace: Optional[WorkspaceManager] = None
_memory: Optional[MemoryStore] = None
_sessions: Optional[SessionStore] = None
_agent: Optional[Any] = None
_pipeline: dict[str, Any] = {}


def get_workspace() -> WorkspaceManager:
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceManager(os.getenv("WORKSPACE_PATH", "./workspace"))
        _workspace.ensure_workspace_exists()
    return _workspace


def get_memory() -> MemoryStore:
    global _memory
    if _memory is None:
        _memory = MemoryStore(get_workspace())
    return _memory


def get_sessions() -> SessionStore:
    global _sessions
    if _sessions is None:
        _sessions = SessionStore(get_workspace())
    return _sessions


def get_pipeline() -> dict[str, Any]:
    if _pipeline.get("coordinator") is None:
        from analyze import load_runtime_env
        from hello_agents import HelloAgentsLLM
        from src.agents.coordinator import create_coordinator
        from src.evaluation import ToolCallCounter

        load_runtime_env()
        llm = HelloAgentsLLM()
        counter = ToolCallCounter()
        _pipeline["llm"] = llm
        _pipeline["counter"] = counter
        _pipeline["coordinator"] = create_coordinator(llm=llm, tool_counter=counter)
    return _pipeline


def get_agent():
    global _agent
    if _agent is None:
        from analyze import load_runtime_env
        from hello_agents import HelloAgentsLLM
        from ..chat.react_agent import CryptoReActAgent

        load_runtime_env()
        workspace = get_workspace()
        llm = get_pipeline()["llm"] if _pipeline.get("llm") else HelloAgentsLLM()
        _agent = CryptoReActAgent(
            workspace=workspace,
            memory=get_memory(),
            sessions=get_sessions(),
            llm=llm,
            get_coordinator=lambda: get_pipeline()["coordinator"],
        )
    return _agent
