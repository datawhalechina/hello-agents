"""Integrated model loop and automatic event wakeups."""

import threading
import time

from .background import (
    collect_background_results, has_pending_background, should_run_background,
    start_background_task,
)
from ..compact.compaction import (
    RecoveryState, block_type, compact_history, is_prompt_too_long_error,
    proactive_compact, reactive_compact, tool_result_budget, with_retry,
)
from ..core.config import (
    CONTEXT_LIMIT, CONTINUATION_PROMPT, DEFAULT_MAX_TOKENS,
    ESCALATED_MAX_TOKENS, MAX_RECOVERY_RETRIES, terminal_print,
)
from ..tasks.cron import (
    CronJob, acknowledge_cron_jobs, consume_cron_queue, cron_lock, cron_queue,
    restore_cron_jobs,
)
from ..core.hooks import trigger_hooks
from ..memory.memory import MEMORY_RUNTIME
from ..tools.mcp import mcp_clients
from ..core.llm import call_message, llm_context, _json_safe
from ..tools.registry import assemble_tool_pool
from ..tools.skills import assemble_system_prompt_parts
from .subagents import has_tool_use
from ..tasks.tasks import release_completed_assignment
from .teams import active_teammates, consume_lead_inbox, format_team_events
from ..tools.tools import call_tool_handler


def _emit_trace(callback, event_type: str, payload: dict):
    """Tracing must never change agent behavior if the UI recorder fails."""
    if callback is None:
        return
    try:
        callback(event_type, payload)
    except Exception as exc:
        terminal_print(f"[trace] recorder error: {type(exc).__name__}: {exc}")


def _emit_messages_snapshot(callback, messages: list) -> None:
    """Push the current message list to the UI so the chat tab updates live.

    The web client polls the conversation record; each snapshot rewrites the
    ``messages`` field and ``updated_at`` so the next poll re-renders without
    waiting for ``agent_loop`` to finish.
    """
    _emit_trace(callback, "messages_snapshot", {"messages": messages})


MAX_TOOL_RESULT_CHARS = 200_000


def _cap_tool_result(output: object) -> object:
    """Truncate oversized tool results before they reach the model context.

    Any tool (not just search) can return a huge payload. Capping it here is
    the last line of defense against a single tool call flooding the context
    window and stalling the agent loop.
    """
    if not isinstance(output, str) or len(output) <= MAX_TOOL_RESULT_CHARS:
        return output
    kept = output[:MAX_TOOL_RESULT_CHARS]
    omitted = len(output) - MAX_TOOL_RESULT_CHARS
    return (
        kept
        + f"\n\n[tool result truncated: showed {MAX_TOOL_RESULT_CHARS} chars, "
        f"omitted {omitted} more chars to protect the context window]"
    )


def _tool_succeeded(output: object) -> bool:
    """Success marker for tool traces.

    Every tool handler reports failure by returning a string that starts with
    "Error", so this single check is enough to aggregate failure rates per tool
    later. Without it there is no way to tell which tool is burning rounds.
    """
    return not str(output).startswith("Error")

# -- Context --


def update_context(context: dict, messages: list) -> dict:
    return {
        "memory_catalog": MEMORY_RUNTIME.read_memory_index(),
        "memories": MEMORY_RUNTIME.load_memories(messages),
        "connected_mcp": list(mcp_clients.keys()),
        "active_teammates": list(active_teammates.keys()),
    }


def remember_after_turn(messages: list) -> None:
    if MEMORY_RUNTIME.extract_memories(messages):
        MEMORY_RUNTIME.consolidate_memories()


# -- Agent Loop --

# Reminder cadence. The reminder must name the tool explicitly: a small model
# ignored 13 rounds of "Update your todos" because nothing mapped that phrase
# to todo_write. Reminders are also capped per loop — a model that ignores the
# first two will ignore the next eleven, which only burn tokens.
TODO_REMINDER_INTERVAL = 3
MAX_TODO_REMINDERS = 2

# Read-only loop brake. One session made 30+ consecutive read-only calls
# (read_file/search_text/glob) without a single edit and never recovered.
# After a streak this long the model has enough context; steer it to act.
READ_ONLY_TOOLS = frozenset({"read_file", "search_text", "glob", "list_dir"})
EDIT_TOOLS = frozenset({"edit_file", "write_file", "apply_patch"})
READ_ONLY_STREAK_THRESHOLD = 6
MAX_LOOP_STEERING = 3

# Task anchor: weak long-context attention drifts mid-task — the agent starts
# reading files the request never needed. Re-injecting the original request
# every few LLM turns re-focuses it and finally elicits text (todo status)
# from models that otherwise emit tool calls only.
TASK_ANCHOR_INTERVAL = 6
MAX_TASK_ANCHORS = 3
TASK_ANCHOR_REQUEST_CHARS = 600

# Hard read-only budget: reminders steer, but a tool-only model can keep
# issuing read_file/search_text forever. Past this many read-only calls
# without any edit since the last one, read-only tools are physically
# blocked until something is edited.
READ_ONLY_HARD_LIMIT = 15

# Loop-level tolerance for transient LLM failures: after with_retry's own
# attempts, a dead connection still must not terminate the whole task.
MAX_TRANSIENT_FAILURES = 3


def _is_transient_failure(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return ("connection" in name or "timeout" in name
            or "connection error" in msg or "timed out" in msg
            or "max retries" in msg)

agent_lock = threading.Lock()


def prepare_context(messages: list, active_request: str, *,
                    session_id: str | None = None, trace_callback=None) -> list:
    # Every LLM turn enters through the same context budget pipeline.
    messages[:] = tool_result_budget(messages)
    messages[:] = proactive_compact(
        messages, active_request, CONTEXT_LIMIT, session_id=session_id,
        trace_callback=trace_callback,
    )
    return messages

def tool_intent_text(active_request: str, messages: list) -> str:
    """Build a bounded local classifier input from the request and recent events."""
    recent = []
    for message in messages[-8:]:
        content = str(message.get("content", ""))
        recent.append(content[:2000])
    return "\n".join([str(active_request), *recent])


def build_user_content(results: list[dict]) -> list[dict]:
    # Tool results and completed background notifications are both returned to
    # the model as user-side content, matching the tool_result feedback loop.
    content = list(results)
    for note in collect_background_results():
        content.append({"type": "text", "text": note})
    return content


def inject_background_notifications(messages: list):
    notes = collect_background_results()
    if notes:
        messages.append({"role": "user", "content": [
            {"type": "text", "text": note} for note in notes]})


def call_llm(messages: list, context: dict, tools: list,
             state: RecoveryState, max_tokens: int, trace_callback=None,
             session_id: str | None = None):
    tool_names = [tool.get("name", "") for tool in tools]
    prompt = assemble_system_prompt_parts(context, tool_names)
    return call_message(
        model=lambda: state.current_model,
        stable_system=prompt["stable"],
        semi_stable_system=prompt["semi_stable"],
        dynamic_system=prompt["dynamic"],
        messages=messages,
        tools=tools,
        max_tokens=max_tokens,
        call_type="agent",
        session_id=session_id,
        retry=lambda invoke: with_retry(invoke, state),
        trace_callback=trace_callback,
    )

def _agent_loop_impl(messages: list, context: dict, active_request: str,
                     trace_callback=None, session_id: str | None = None):
    tools, handlers = assemble_tool_pool(tool_intent_text(active_request, messages))
    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS

    # Loop-local reminder state: these were module-global, so counters leaked
    # across turns and sessions.
    rounds_since_todo = 0
    todo_reminders_sent = 0
    read_only_streak = 0
    loop_steering_sent = 0
    llm_turns = 0
    task_anchors_sent = 0
    read_only_total = 0
    transient_failures = 0

    unacknowledged_cron_jobs: list[CronJob] = []
    while True:
        # One cycle: inject scheduled/background work, prepare context, call
        # the model, execute tool_use blocks, append tool_results, repeat.
        fired = consume_cron_queue()
        unacknowledged_cron_jobs.extend(fired)
        for job in fired:
            messages.append({"role": "user",
                             "content": f"[Scheduled] {job.prompt}"})
            print(f"  \033[35m[cron inject] {job.prompt[:60]}\033[0m")
        if fired:
            scheduled_requests = "\n".join(
                f"Run scheduled task: {job.prompt}" for job in fired)
            active_request = f"{active_request}\n{scheduled_requests}".strip()

        inject_background_notifications(messages)

        if (rounds_since_todo >= TODO_REMINDER_INTERVAL
                and todo_reminders_sent < MAX_TODO_REMINDERS):
            messages.append({"role": "user", "content":
                             "<reminder>Update your task list now by calling "
                             "the todo_write tool.</reminder>"})
            todo_reminders_sent += 1
            rounds_since_todo = 0

        prepare_context(messages, active_request, session_id=session_id,
                        trace_callback=trace_callback)
        _emit_messages_snapshot(trace_callback, messages)
        context = update_context(context, messages)
        tools, handlers = assemble_tool_pool(tool_intent_text(active_request, messages))

        try:
            response = call_llm(messages, context, tools, state, max_tokens,
                                trace_callback, session_id)
        except Exception as e:
            if is_prompt_too_long_error(e) and not state.has_attempted_reactive_compact:
                messages[:] = reactive_compact(
                    messages, active_request, session_id=session_id,
                    trace_callback=trace_callback)
                _emit_messages_snapshot(trace_callback, messages)
                state.has_attempted_reactive_compact = True
                continue
            if _is_transient_failure(e) and transient_failures < MAX_TRANSIENT_FAILURES:
                # A network blip must not end the task: the session died this
                # way right after steering reminders were injected, so the
                # model never even saw them. Back off and re-run the cycle.
                transient_failures += 1
                delay = min(2.0 * transient_failures, 15.0)
                print(f"  \033[33m[net] {type(e).__name__}; "
                      f"cycle retry {transient_failures}/"
                      f"{MAX_TRANSIENT_FAILURES} after {delay:.0f}s\033[0m")
                time.sleep(delay)
                continue
            restore_cron_jobs(unacknowledged_cron_jobs)
            messages.append({"role": "assistant", "content": [
                {"type": "text", "text": f"[Error] {type(e).__name__}: {e}"}]})
            _emit_messages_snapshot(trace_callback, messages)
            release_completed_assignment("agent")
            return

        acknowledge_cron_jobs(unacknowledged_cron_jobs)
        unacknowledged_cron_jobs.clear()
        llm_turns += 1

        if response.stop_reason == "max_tokens":
            if not state.has_escalated:
                max_tokens = ESCALATED_MAX_TOKENS
                state.has_escalated = True
                print(f"  \033[33m[max_tokens] retry with {max_tokens}\033[0m")
                continue
            messages.append({"role": "assistant", "content": _json_safe(response.content)})
            _emit_messages_snapshot(trace_callback, messages)
            if state.recovery_count < MAX_RECOVERY_RETRIES:
                messages.append({"role": "user", "content": CONTINUATION_PROMPT})
                _emit_messages_snapshot(trace_callback, messages)
                state.recovery_count += 1
                continue
            release_completed_assignment("agent")
            return

        max_tokens = DEFAULT_MAX_TOKENS
        state.has_escalated = False
        messages.append({"role": "assistant", "content": _json_safe(response.content)})
        _emit_messages_snapshot(trace_callback, messages)
        if not has_tool_use(response.content):
            trigger_hooks("Stop", messages)
            remember_after_turn(messages)
            release_completed_assignment("agent")
            return

        results = []
        compact_requested = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")

            if block.name == "compact":
                _emit_trace(trace_callback, "tool_call", {"name": block.name, "id": block.id, "input": block.input})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "[Compaction requested. This completed turn will be summarized.]",
                })
                compact_requested = True
                _emit_trace(trace_callback, "tools_result", {"tool_use_id": block.id, "name": block.name, "content": "[Compaction requested. This completed turn will be summarized.]"})
                continue

            _emit_trace(trace_callback, "tool_call", {"name": block.name, "id": block.id, "input": block.input})
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(blocked)})
                _emit_trace(trace_callback, "tools_result", {"tool_use_id": block.id, "name": block.name, "content": str(blocked), "blocked": True, "ok": False})
                continue

            if should_run_background(block.name, block.input):
                try:
                    bg_id = start_background_task(block, handlers)
                    output = (f"[Background task {bg_id} started] "
                              "Result will arrive as a task_notification.")
                except Exception as exc:
                    output = (f"Error: Failed to start background task: "
                              f"{type(exc).__name__}: {exc}")
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output})
                _emit_trace(trace_callback, "tools_result", {"tool_use_id": block.id, "name": block.name, "content": output, "background": True, "ok": _tool_succeeded(output)})
                continue

            handler = handlers.get(block.name)
            if (block.name in READ_ONLY_TOOLS
                    and read_only_total >= READ_ONLY_HARD_LIMIT):
                # Reminders steer; this physically stops exploration. A
                # tool-only model ignored every steering reminder and kept
                # issuing read_file — budget exhaustion is the final brake.
                output = (
                    f"[read-only budget exhausted: {read_only_total} "
                    "read-only calls in this turn without a single edit. "
                    "Further exploration is blocked. Make the change now "
                    "with edit_file or apply_patch, or reply in text with "
                    "the final result.]"
                )
            else:
                output = call_tool_handler(handler, block.input, block.name)
            output = _cap_tool_result(output)
            trigger_hooks("PostToolUse", block, output)
            print(str(output)[:300])

            if block.name == "todo_write":
                rounds_since_todo = 0
            else:
                rounds_since_todo += 1
            if block.name in EDIT_TOOLS:
                read_only_streak = 0
                read_only_total = 0
            elif block.name in READ_ONLY_TOOLS:
                read_only_streak += 1
                read_only_total += 1

            results.append({"type": "tool_result",
                            "tool_use_id": block.id, "content": output})
            _emit_trace(trace_callback, "tools_result", {
                "tool_use_id": block.id, "name": block.name,
                "input": block.input, "content": output,
                "ok": _tool_succeeded(output),
            })

        messages.append({"role": "user", "content": build_user_content(results)})
        _emit_messages_snapshot(trace_callback, messages)
        if (llm_turns % TASK_ANCHOR_INTERVAL == 0
                and task_anchors_sent < MAX_TASK_ANCHORS):
            request_excerpt = active_request[:TASK_ANCHOR_REQUEST_CHARS]
            messages.append({"role": "user", "content":
                             f"<task-focus>\nOriginal request: "
                             f"{request_excerpt}\nRe-read it and continue "
                             "working toward exactly this goal: report which "
                             "todo steps are done, then take the single next "
                             "action. Stay inside the request's scope — no "
                             "new files, refactors, or exploration the "
                             "request does not need. If you already have "
                             "enough context, start editing now.\n"
                             "</task-focus>"})
            _emit_messages_snapshot(trace_callback, messages)
            task_anchors_sent += 1
        if (read_only_streak >= READ_ONLY_STREAK_THRESHOLD
                and loop_steering_sent < MAX_LOOP_STEERING):
            messages.append({"role": "user", "content":
                             f"<reminder>You have made {read_only_streak} "
                             "consecutive read-only tool calls "
                             "(read_file/search_text/glob/list_dir) without "
                             "editing anything. Stop exploring: you already "
                             "have enough context. Make the change now with "
                             "edit_file or apply_patch, or reply in text "
                             "explaining exactly what is blocking "
                             "you.</reminder>"})
            _emit_messages_snapshot(trace_callback, messages)
            loop_steering_sent += 1
            read_only_streak = 0
        if compact_requested:
            messages[:] = compact_history(
                messages, active_request, session_id=session_id,
                trace_callback=trace_callback)
            _emit_messages_snapshot(trace_callback, messages)


def agent_loop(messages: list, context: dict, active_request: str,
               trace_callback=None, session_id: str | None = None):
    with llm_context(session_id, trace_callback):
        return _agent_loop_impl(
            messages, context, active_request, trace_callback, session_id
        )


def print_turn_assistants(messages: list, turn_start: int):
    for msg in messages[turn_start:]:
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content", []):
            if block_type(block) == "text":
                terminal_print(block["text"] if isinstance(block, dict) else block.text)


def async_event_loop(history: list, context: dict, session_state: dict):
    while True:
        time.sleep(1)
        with agent_lock:
            with cron_lock:
                fired = list(cron_queue)
            inbox = consume_lead_inbox(route_protocol=True)
            if not fired and not inbox and not has_pending_background():
                continue
            turn_start = len(history)
            scheduled_requests = []
            for job in fired:
                scheduled_requests.append(f"Run scheduled task: {job.prompt}")
                terminal_print(
                    f"  \033[35m[cron auto] {job.prompt[:60]}\033[0m")
            if inbox:
                history.append({"role": "user",
                                "content": format_team_events(inbox)})
                terminal_print(
                    f"  \033[33m[team auto] {len(inbox)} events\033[0m")
            active_request = (
                "\n".join(scheduled_requests)
                if scheduled_requests
                else session_state["active_user_request"]
            )
            agent_loop(history, context, active_request)
            context.update(update_context(context, history))
            print_turn_assistants(history, turn_start)
