"""Runtime platform facts, probed once and injected into the model prompt.

Cross-platform command failures are mostly information asymmetry: the model
writes POSIX by reflex and only discovers the host is Windows after a failed
round. Probing once at startup and stating the facts up front moves that
discovery before the call instead of after it.

Modeled on Codex's `shell_detect.rs`, which guarantees `default_user_shell()`
never returns empty: a probe that comes back "unknown" is not neutral, it
pushes the problem back onto the model.
"""

import os
import platform
import shutil
from functools import lru_cache

# Probed with shutil.which rather than hardcoded: a Windows box with Git for
# Windows on PATH really does have ls/grep/head, and telling the model those
# are missing would needlessly shrink what it can do.
PROBE_COMMANDS = (
    "ls", "cat", "grep", "sed", "awk", "find", "head", "tail",
    "touch", "which", "rm", "cp", "mv", "git", "python3",
)

# Built-in replacements offered when a probed command is unavailable.
SUGGESTIONS = {
    "ls": "list_dir",
    "cat": "read_file",
    "grep": "search_text",
    "sed": "edit_file",
    "awk": "read_file",
    "find": "glob",
    "head": "read_file with limit",
    "tail": "read_file with offset",
    "touch": "write_file",
    "which": "list_dir",
    "rm": "apply_patch",
    "cp": "read_file then write_file",
    "mv": "read_file then write_file",
}


def _resolve(command: str) -> str | None:
    try:
        return shutil.which(command)
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=1)
def platform_facts() -> dict:
    """Probe the host once. Always returns a usable answer, never empty."""
    is_windows = os.name == "nt"
    system = platform.system() or ("Windows" if is_windows else "Unix")
    native_shell = "cmd.exe" if is_windows else "/bin/sh"

    if is_windows:
        # Git for Windows puts a POSIX shell on PATH; WSL and Cygwin do not
        # reliably appear here, so treat this as best-effort only.
        posix_shell = _resolve("bash") or _resolve("sh")
    else:
        posix_shell = _resolve("bash") or _resolve("zsh") or "/bin/sh"

    available: list[str] = []
    missing: list[str] = []
    for command in PROBE_COMMANDS:
        (available if _resolve(command) else missing).append(command)

    return {
        "system": system,
        "release": platform.release() or "",
        "machine": platform.machine() or "",
        "is_windows": is_windows,
        "native_shell": native_shell,
        "posix_shell": posix_shell or "",
        "available": tuple(available),
        "missing": tuple(missing),
    }


def missing_commands() -> tuple[str, ...]:
    return platform_facts()["missing"]


def suggestion_for(command: str) -> str:
    return SUGGESTIONS.get(command, "the equivalent built-in tool")


def platform_brief() -> str:
    """Stable-across-the-run facts for the system prompt.

    Constant within a process, so it belongs in the cacheable prefix.
    """
    facts = platform_facts()
    host = " ".join(
        part for part in (facts["system"], facts["release"]) if part)
    lines = [
        f"Environment: {host} ({facts['machine']})",
        f"Shell used by the bash tool: {facts['native_shell']}",
    ]
    if facts["posix_shell"]:
        lines.append(f"POSIX shell on PATH: {facts['posix_shell']}")
    if facts["available"]:
        lines.append("Commands available here: " + ", ".join(facts["available"]))
    if facts["missing"]:
        lines.append(
            "Commands NOT available here: " + ", ".join(facts["missing"]))
    if facts["is_windows"]:
        lines.append(
            "cmd.exe has no single-quote grouping and does not strip double "
            "quotes. Prefer list_dir, glob, search_text, and read_file over "
            "shell one-liners."
        )
    return "\n".join(lines)


def bash_description() -> str:
    """Platform-aware description for the bash tool schema.

    The description is the only thing the model reads before choosing an
    argument, so it carries the unavailable-command list.
    """
    facts = platform_facts()
    parts = [
        f"Run a shell command via {facts['native_shell']} on "
        f"{facts['system']} and return its output.\n"
        "Use it for what the built-in tools cannot do: installs, build, "
        "typecheck, tests, git, dev servers. To read or change files use "
        "read_file, search_text, glob, list_dir, edit_file, write_file."
    ]
    if facts["missing"]:
        parts.append(
            "Unavailable on this host: " + ", ".join(facts["missing"])
            + " — do not build one-liners on them.")
    parts.append(
        "Non-interactive commands only; run_in_background for long ones."
    )
    return " ".join(parts)
