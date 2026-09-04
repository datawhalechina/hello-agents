"""Modular coding assistant runtime.

Layout:
    core/    infrastructure: config, workspace, llm, storage, hooks, filelock
    agent/   orchestration: agent loop, subagents, teams, background tasks
    memory/  long-term memory runtime adapter
    compact/ context compaction for long conversations
    tools/   built-in tools, registry, MCP clients, skill loading
    tasks/   task management and cron scheduling
"""

__all__ = ["agent", "cli", "compact", "core", "memory", "tasks", "tools", "web"]
