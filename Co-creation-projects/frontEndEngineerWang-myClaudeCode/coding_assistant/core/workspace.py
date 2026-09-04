"""Context-local workspace selection for interactive conversations."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .config import WORKDIR

_ACTIVE_WORKDIR: ContextVar[Path | None] = ContextVar("active_workdir", default=None)


def current_workdir() -> Path:
    """Return the workspace for the current agent turn."""
    return _ACTIVE_WORKDIR.get() or WORKDIR


@contextmanager
def use_workdir(path: str | Path):
    """Run a turn with a conversation-specific workspace."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Working directory does not exist: {resolved}")
    token = _ACTIVE_WORKDIR.set(resolved)
    try:
        yield resolved
    finally:
        _ACTIVE_WORKDIR.reset(token)
