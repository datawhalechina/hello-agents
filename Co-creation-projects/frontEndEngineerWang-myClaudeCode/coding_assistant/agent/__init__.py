"""Conversation orchestration: agent loop, subagents, teams, background tasks.

NOTE: do NOT re-export submodules here (`from . import agent`). agent.py
imports tools.registry / compact.compaction at top level, and those modules
import agent.subagents / agent.teams; eagerly importing the agent package
here would turn that into a circular import. `from coding_assistant.agent
import agent` still works — Python falls back to importing the submodule.
"""
