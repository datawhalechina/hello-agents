"""Tool lifecycle hooks and host-owned permission policy."""

import ast
import json
import re
import threading

from .config import CONSOLE, PERMISSION_MODE, WORKDIR, terminal_print
from .workspace import current_workdir


def _coerce_input_value(inp):
    """Return a tool input as a dict.

    The Anthropic SDK normally delivers ``tool_use.input`` as a parsed object.
    A serialized JSON string can still reach us (replayed web sessions, or a
    model that emitted a string), which makes ``.get()`` calls raise
    ``AttributeError``. Coerce it so dispatch and permission checks stay safe.
    """
    if isinstance(inp, dict):
        return inp
    if isinstance(inp, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(inp)
            except (ValueError, SyntaxError):
                continue
            if isinstance(parsed, dict):
                return parsed
        return {}
    return {}


def _coerce_tool_input(block):
    """Extract and coerce the input dict from a tool_use ``block``."""
    if isinstance(block, dict):
        return _coerce_input_value(block.get("input"))
    return _coerce_input_value(getattr(block, "input", None))

HOOKS = {"UserPromptSubmit": [], "PreToolUse": [],
         "PostToolUse": [], "Stop": []}


def register_hook(event: str, callback):
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None


ALWAYS_DENY_RULES = [
    (re.compile(r"(?i)(?:^|[;&|]\s*)(?:sudo|runas)(?:\s|$)"),
     "privilege escalation is not allowed"),
    (re.compile(r"(?i)(?:^|[;&|]\s*)(?:shutdown|reboot|poweroff|halt)(?:\s|$)"),
     "system power commands are not allowed"),
    (re.compile(r"(?i)(?:^|[;&|]\s*)(?:mkfs(?:\.[a-z0-9]+)?|diskpart|format)(?:\s|$)"),
     "disk formatting commands are not allowed"),
    (re.compile(r"(?i)(?:^|[;&|]\s*)dd\s+[^;&|]*\bof="),
     "raw disk writes are not allowed"),
    (re.compile(r"rm\s+-[^\r\n]*r[^\r\n]*f[^\r\n]*(?:\s+/|\s+~)(?:\s|$)", re.IGNORECASE),
     "recursive deletion of a root directory is not allowed"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
     "process fork bombs are not allowed"),
]

FULL_MODE_CONFIRM_RULES = [
    (re.compile(
        r"(?i)(?:^|[;&|]\s*)(?:rm|rmdir|del|erase|rd|remove-item)(?:\s|$)"
    ), "destructive file deletion requires request mode"),
    (re.compile(r"(?i)\bgit\s+(?:reset\s+--hard|clean\s+-[^\s]*f|checkout\s+--|restore\s+)"),
     "destructive Git recovery requires request mode"),
    (re.compile(r"(?i)\b(?:powershell|pwsh)\b[^\r\n]*-(?:enc|encodedcommand)\b"),
     "encoded PowerShell commands are not transparent enough for full mode"),
    (re.compile(
        r"(?i)(?:^|[;&|]\s*)(?:cd|chdir|pushd|set-location)\s+"
        r"[\"']?(?:\.\.(?:[\\/]|(?=[\s\"']|$))|[a-z]:[\\/]|/|\\\\)"
    ), "changing the shell outside the workspace requires request mode"),
    (re.compile(
        r"(?:^|\s)(?:>|>>|2>|2>>)\s*[\"']?"
        r"(?:\.\.(?:[\\/]|(?=[\s\"']|$))|[a-zA-Z]:[\\/]|/|\\\\)"
    ), "redirecting output outside the workspace requires request mode"),
]
mcp_tool_policies: dict[str, str] = {}


def classify_bash_command(
    command: str, mode: str | None = None
) -> tuple[str, str | None]:
    """Return (deny|confirm|allow, reason) for a shell command."""
    mode = mode or PERMISSION_MODE
    if not isinstance(command, str):
        return "deny", "shell command must be a string"
    if not command.strip():
        return "deny", "shell command cannot be empty"
    if "\0" in command:
        return "deny", "shell command cannot contain NUL bytes"
    if len(command) > 20_000:
        return "deny", "shell command is too long"
    normalized = re.sub(r"\s+", " ", command.strip())
    for pattern, reason in ALWAYS_DENY_RULES:
        if pattern.search(normalized):
            return "deny", reason
    if mode == "full":
        for pattern, reason in FULL_MODE_CONFIRM_RULES:
            if pattern.search(normalized):
                return "confirm", reason
        return "allow", None
    return "confirm", "request mode requires approval"


def validate_bash_command(command: str, mode: str | None = None) -> str | None:
    """Return only permanent-denial reasons for compatibility with callers."""
    action, reason = classify_bash_command(command, mode)
    return reason if action == "deny" else None


def permission_hook(block):
    # The permission layer sees the raw tool_use before dispatch. It can deny,
    # ask the user, or allow execution to continue.
    data = _coerce_tool_input(block)
    if block.name == "bash":
        command = data.get("command", "")
        action, reason = classify_bash_command(command)
        if action == "deny":
            return f"Permission denied: {reason}"
        if action == "allow":
            terminal_print(f"\033[90m[permission:auto] {command}\033[0m")
            return None
        if threading.current_thread() is not threading.main_thread():
            return ("Permission denied: interactive shell approval is unavailable "
                    f"during an asynchronous turn ({reason})")
        label = "risky shell command" if PERMISSION_MODE == "full" else "shell command"
        terminal_print(f"\n\033[33m[permission] {label}\033[0m")
        if PERMISSION_MODE == "full" and reason:
            terminal_print(f"  Safeguard: {reason}")
        terminal_print(f"  {command}")
        choice = CONSOLE.ask("  Allow? [y/N] ").strip().lower()
        if choice not in ("y", "yes"):
            return "Permission denied by user"
    if block.name in ("read_file", "write_file", "edit_file"):
        path = data.get("path", "")
        if not isinstance(path, str):
            return "Permission denied: path must be a string"
        if not (current_workdir() / path).resolve().is_relative_to(current_workdir()):
            return "Permission denied: path is outside the workspace"
    if block.name == "apply_patch":
        patches = data.get("patches")
        if not isinstance(patches, list):
            return "Permission denied: patches must be a list"
        for patch in patches:
            path = patch.get("path") if isinstance(patch, dict) else None
            if not isinstance(path, str):
                return "Permission denied: every patch path must be a string"
            if not (current_workdir() / path).resolve().is_relative_to(current_workdir()):
                return f"Permission denied: path is outside the workspace: {path}"
    if block.name.startswith("mcp__"):
        policy = mcp_tool_policies.get(block.name, "confirm")
        if policy == "deny":
            return f"Permission denied by host policy: {block.name}"
        if policy == "allow":
            return None
        if PERMISSION_MODE == "full":
            terminal_print(
                f"\033[90m[permission:auto] MCP tool: {block.name}\033[0m"
            )
            return None
        if threading.current_thread() is not threading.main_thread():
            return ("Permission denied: interactive MCP approval is unavailable "
                    "during an asynchronous turn")
        terminal_print(f"\n\033[33m[permission] MCP tool: {block.name}\033[0m")
        choice = CONSOLE.ask("  Allow? [y/N] ").strip().lower()
        if choice not in ("y", "yes"):
            return "Permission denied by user"
    return None


def log_hook(block):
    print(f"\033[90m[HOOK] {block.name}\033[0m")
    return None


def large_output_hook(block, output):
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] large output from {block.name}: "
              f"{len(str(output))} chars\033[0m")
    return None


def user_prompt_hook(query: str):
    print(f"\033[90m[HOOK] UserPromptSubmit: {current_workdir()}\033[0m")
    return None


def stop_hook(messages: list):
    tool_count = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            tool_count += sum(1 for item in content
                              if isinstance(item, dict)
                              and item.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: {tool_count} tool result(s)\033[0m")
    return None


register_hook("UserPromptSubmit", user_prompt_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", stop_hook)


# -- Subagent Tool --
