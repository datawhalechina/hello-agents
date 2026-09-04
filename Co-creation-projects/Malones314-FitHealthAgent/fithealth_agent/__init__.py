"""FitHealthAgent public package API.

Importing data, parsing, or validation modules must not initialize the
optional LLM stack. The public factory remains available at package level,
but imports its implementation only when it is called.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Iterable

_PYTHON_VERSION = sys.version_info
if _PYTHON_VERSION < (3, 11):
    raise RuntimeError(
        "FitHealthAgent requires Python 3.11 or newer; "
        f"current interpreter is {_PYTHON_VERSION[0]}.{_PYTHON_VERSION[1]}."
    )

if TYPE_CHECKING:
    from hello_agents import ReActAgent


def create_fithealth_agent(
    *, avoid_youtube_channels: Iterable[str] | None = None
) -> "ReActAgent":
    """Create the LLM-backed agent, loading its dependencies on demand."""
    from .agent import create_fithealth_agent as _create_fithealth_agent

    return _create_fithealth_agent(
        avoid_youtube_channels=avoid_youtube_channels,
    )

__all__ = ["create_fithealth_agent"]
