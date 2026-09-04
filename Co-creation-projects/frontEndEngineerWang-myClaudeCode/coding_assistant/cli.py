"""Interactive command-line host for the coding assistant."""

import threading

from .core import config
from .agent.agent import (
    agent_lock, agent_loop, async_event_loop, print_turn_assistants,
    update_context,
)
from .tasks.cron import start_runtime_services
from .core.hooks import trigger_hooks


def main() -> None:
    config.CLI_ACTIVE = True
    start_runtime_services()
    print(f"Permission mode: {config.PERMISSION_MODE}")
    print("Enter a question, press Enter to send. Type q to quit.\n")
    history = []
    context = update_context({}, [])
    session_state = {"active_user_request": "(no active user request)"}
    threading.Thread(
        target=async_event_loop,
        args=(history, context, session_state),
        daemon=True,
    ).start()
    while True:
        try:
            query = config.CONSOLE.ask(config.PROMPT)
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        with agent_lock:
            trigger_hooks("UserPromptSubmit", query)
            turn_start = len(history)
            session_state["active_user_request"] = query
            history.append({"role": "user", "content": query})
            agent_loop(history, context, query)
            context = update_context(context, history)
            print_turn_assistants(history, turn_start)
        print()
