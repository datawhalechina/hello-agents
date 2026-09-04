"""Asynchronous shell execution and task notifications."""

import threading

from ..core.hooks import _coerce_tool_input, trigger_hooks
from ..tools.tools import _agent_cwd, _format_bash_result, _run_bash_process

# -- Background Tasks --

# Slow tools return a placeholder tool_result immediately. Their real output is
# later injected as a task_notification, so the main loop can keep moving.
_bg_counter = 0
background_tasks: dict[str, dict] = {}
background_results: dict[str, str] = {}
background_lock = threading.Lock()


def should_run_background(tool_name: str, tool_input: dict) -> bool:
    if isinstance(tool_input, str):
        tool_input = _coerce_tool_input(tool_input)
    return (
        tool_name == "bash"
        and tool_input.get("run_in_background") is True
    )


def start_background_task(block, handlers: dict) -> str:
    global _bg_counter
    data = _coerce_tool_input(block)
    command = data.get("command", block.name)
    cwd, cwd_error = _agent_cwd()

    def worker():
        try:
            if block.name != "bash":
                raise ValueError("only bash can run in the background")
            if cwd_error:
                raise ValueError(cwd_error.removeprefix("Error: "))
            output, exit_code = _run_bash_process(
                str(data["command"]), cwd)
            result = _format_bash_result(output, exit_code)
            status = "completed" if exit_code == 0 else "failed"
        except Exception as exc:
            result = f"Error: {type(exc).__name__}: {exc}"
            status = "failed"
        try:
            trigger_hooks("PostToolUse", block, result)
        except Exception as exc:
            result = (f"Error: PostToolUse hook failed: "
                      f"{type(exc).__name__}: {exc}\n{result}")
            status = "failed"
        with background_lock:
            task = background_tasks.get(bg_id)
            if task is None:
                return
            task["status"] = status
            background_results[bg_id] = str(result)

    with background_lock:
        _bg_counter += 1
        bg_id = f"bg_{_bg_counter:04d}"
        background_tasks[bg_id] = {
            "tool_use_id": block.id,
            "command": command,
            "status": "running",
            "cwd": str(cwd) if cwd else None,
        }
    thread = threading.Thread(target=worker, daemon=True)
    try:
        thread.start()
    except Exception:
        with background_lock:
            background_tasks.pop(bg_id, None)
            background_results.pop(bg_id, None)
        raise
    print(f"  \033[33m[background] {bg_id}: {str(command)[:60]}\033[0m")
    return bg_id


def collect_background_results() -> list[str]:
    with background_lock:
        ready = [bg_id for bg_id, task in background_tasks.items()
                 if task["status"] in {"completed", "failed"}]
        completed = [
            (bg_id, background_tasks.pop(bg_id),
             background_results.pop(bg_id, ""))
            for bg_id in ready
        ]
    notifications = []
    for bg_id, task, output in completed:
        summary = output[:200] if len(output) > 200 else output
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{bg_id}</task_id>\n"
            f"  <status>{task['status']}</status>\n"
            f"  <command>{task['command']}</command>\n"
            f"  <summary>{summary}</summary>\n"
            f"</task_notification>")
    return notifications


def has_pending_background() -> bool:
    """Return whether terminal background work is waiting for delivery."""
    with background_lock:
        return any(task["status"] in {"completed", "failed"}
                   for task in background_tasks.values())


# -- Cron Scheduler --

# Cron jobs are stored separately from conversation history. When a job fires,
# it becomes a scheduled prompt that is injected back into the same agent loop.
