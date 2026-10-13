"""Compatibility split point for the logout workflow."""

from __future__ import annotations

from fithealth_agent.workflows.upload_workflow import WorkflowResult
from fithealth_agent.workflows.upload_workflow import logout as _logout


def logout(payload: dict | None = None) -> WorkflowResult:
    """Run logout memory routing and return a transport-neutral result."""
    return _logout(payload)
