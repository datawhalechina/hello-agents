"""CLI UI helpers (ANSI colors, spinner, consistent formatting).

Kept dependency-free to avoid pulling extra packages into the MVP.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Iterable


RESET = "\x1b[0m"
PRIMARY = "\x1b[38;2;120;200;255m"
ACCENT = "\x1b[38;2;150;140;255m"
INFO = "\x1b[38;2;120;120;120m"
WARN = "\x1b[38;2;255;190;120m"
ERROR = "\x1b[38;2;255;120;120m"


def supports_ansi() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def c(text: str, color: str) -> str:
    if not supports_ansi():
        return text
    return f"{color}{text}{RESET}"


def hr(char: str = "=", width: int = 80) -> str:
    return char * width


def clamp_text(text: str, limit: int = 40_000) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n...<truncated {len(text) - limit} chars>"


def log_tool_event(name: str, message: str) -> None:
    """LangChain-demo-like tool logging."""
    header = f"⏺ {name}"
    print(c(header, ACCENT))
    lines: Iterable[str] = message.splitlines() if message else [""]
    for line in lines:
        print(f"  ⎿ {line}")


class Spinner:
    """Simple terminal spinner."""

    def __init__(self, label: str = "Thinking…") -> None:
        self.label = label
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._index = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not supports_ansi() or self._running:
            return
        self._running = True

        def _run() -> None:
            while self._running:
                frame = self.frames[self._index % len(self.frames)]
                self._index += 1
                print(c(f"{frame} {self.label}", INFO), end="\r", flush=True)
                time.sleep(0.08)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if supports_ansi():
            print("\r\x1b[2K", end="", flush=True)
