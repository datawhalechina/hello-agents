from __future__ import annotations

from pathlib import Path

from hello_agents.core.config import Config

from ...settings import get_settings


def papergraph_agent_config() -> Config:
    memory_root = Path(get_settings().data_dir).resolve() / "memory"
    return Config(
        debug=bool(get_settings().debug),
        log_level=str(get_settings().log_level or "INFO"),
        trace_dir=str(memory_root / "traces"),
        session_dir=str(memory_root / "sessions"),
        tool_output_dir=str(memory_root / "tool-output"),
        skills_dir=str(memory_root / "skills"),
        todowrite_persistence_dir=str(memory_root / "todos"),
        devlog_persistence_dir=str(memory_root / "devlogs"),
    )
