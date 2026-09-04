"""Built-in tool schemas, handlers, and dynamic MCP tool assembly."""

from ..tasks.cron import run_cancel_cron, run_list_crons, run_schedule_cron
from .mcp import MCP_HOST_POLICY, connect_mcp, mcp_clients, normalize_mcp_name
from .skills import load_skill
from ..agent.subagents import spawn_subagent
from ..tasks.tasks import claim_task, complete_task, create_task, create_worktree, get_task_json, list_tasks
from ..agent.teams import (
    BUS, active_teammates, run_request_plan, run_request_shutdown,
    run_review_plan, spawn_teammate_thread, team_lock,
)
from ..core.platform import bash_description
from .tools import (
    APPLY_PATCH_TOOL, SEARCH_TEXT_TOOL, run_agent_apply_patch, run_agent_bash,
    run_agent_edit, run_agent_glob, run_agent_list_dir, run_agent_read,
    run_agent_search_text, run_agent_write, run_todo_write,
)

CORE_TOOL_NAMES = {
    "bash", "read_file", "write_file", "edit_file", "glob", "list_dir",
    "search_text", "apply_patch", "todo_write", "load_skill", "compact",
    "connect_mcp",
}
TASK_TOOL_NAMES = {
    "task", "create_task", "list_tasks", "get_task", "claim_task",
    "complete_task",
}
CRON_TOOL_NAMES = {"schedule_cron", "list_crons", "cancel_cron"}
TEAM_TOOL_NAMES = {
    "spawn_teammate", "list_teammates", "send_message", "request_shutdown",
    "request_plan", "review_plan", "create_worktree",
}

TASK_KEYWORDS = (
    "task", "任务", "计划", "依赖", "worktree", "subagent", "delegate",
    "delegation", "子代理",
)
CRON_KEYWORDS = ("cron", "定时", "schedule", "scheduled", "调度")
TEAM_KEYWORDS = (
    "teammate", "team", "团队", "并行", "协作", "parallel", "multi-agent",
)


def select_tool_names(intent_text: str = "") -> set[str]:
    """Select deterministic tool groups without spending an LLM request."""
    normalized = str(intent_text or "").casefold()
    selected = set(CORE_TOOL_NAMES)
    if any(keyword in normalized for keyword in TASK_KEYWORDS):
        selected.update(TASK_TOOL_NAMES)
    if any(keyword in normalized for keyword in CRON_KEYWORDS):
        selected.update(CRON_TOOL_NAMES)
    if any(keyword in normalized for keyword in TEAM_KEYWORDS):
        selected.update(TEAM_TOOL_NAMES)
        selected.update(TASK_TOOL_NAMES)
    return selected


def assemble_tool_pool(intent_text: str = "", *, include_all: bool = False
                       ) -> tuple[list[dict], dict]:
    """Merge selected built-ins and relevant MCP tools in a stable order."""
    from ..core import hooks

    selected = ({tool["name"] for tool in builtin_tools()}
                if include_all else select_tool_names(intent_text))
    builtins = builtin_tools()
    tools = [tool for tool in builtins if tool["name"] in selected]
    handlers = {name: BUILTIN_HANDLERS[name]
                for name in (tool["name"] for tool in tools)
                if name in BUILTIN_HANDLERS}
    policies: dict[str, str] = {}
    origins = {tool["name"]: f"built-in tool {tool['name']!r}"
               for tool in tools}
    normalized_intent = str(intent_text or "").casefold()

    for server_name in sorted(mcp_clients):
        # MCP schemas are only sent when the task names the connected server.
        if not include_all and server_name.casefold() not in normalized_intent:
            continue
        mcp_client = mcp_clients[server_name]
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            raw_name = tool_def["name"]
            safe_tool = normalize_mcp_name(raw_name)
            prefixed = f"mcp__{safe_server}__{safe_tool}"
            if len(prefixed) > 64:
                raise ValueError(
                    f"MCP tool name is longer than 64 characters: {prefixed}"
                )
            origin = f"MCP tool {server_name!r}/{raw_name!r}"
            if prefixed in origins:
                raise ValueError(
                    "MCP tool name collision after normalization: "
                    f"{prefixed!r} maps both {origins[prefixed]} and {origin}"
                )
            schema = tool_def.get("inputSchema", {})
            if not isinstance(schema, dict) or schema.get("type", "object") != "object":
                raise ValueError(f"Invalid input schema for {origin}")
            origins[prefixed] = origin
            tools.append({
                "name": prefixed,
                "description": tool_def.get("description", ""),
                "input_schema": schema,
            })
            handlers[prefixed] = (
                lambda *, client=mcp_client, tool=raw_name, **kwargs:
                client.call_tool(tool, kwargs)
            )
            policies[prefixed] = MCP_HOST_POLICY.get(
                (server_name, raw_name), "confirm"
            )
    hooks.mcp_tool_policies = policies
    return tools, handlers
# -- Lead Worktree Tools --

def run_create_worktree(name: str, task_id: str) -> str:
    return create_worktree(name, task_id)

# -- Basic Tool Handlers --

def run_create_task(subject: str, description: str = "",
                    blockedBy: list[str] | None = None) -> str:
    task = create_task(subject, description, blockedBy)
    deps = f" (blockedBy: {', '.join(blockedBy)})" if blockedBy else ""
    print(f"  \033[34m[create] {task.subject}{deps}\033[0m")
    return f"Created {task.id}: {task.subject}{deps}"


def run_list_tasks() -> str:
    tasks = list_tasks()
    if not tasks:
        return "No tasks."
    return "\n".join(
        f"  {t.id}: {t.subject} [{t.status}]"
        + (f" (wt:{t.worktree})" if t.worktree else "")
        for t in tasks)


def run_get_task(task_id: str) -> str:
    try:
        return get_task_json(task_id)
    except ValueError as exc:
        return f"Error: {exc}"
    except FileNotFoundError:
        return f"Error: task {task_id} not found"

def run_claim_task(task_id: str) -> str:
    try:
        return claim_task(task_id, owner="agent")
    except ValueError as exc:
        return f"Error: {exc}"
    except FileNotFoundError:
        return f"Error: task {task_id} not found"

def run_complete_task(task_id: str) -> str:
    try:
        return complete_task(task_id, owner="agent")
    except ValueError as exc:
        return f"Error: {exc}"
    except FileNotFoundError:
        return f"Error: task {task_id} not found"

def run_spawn_teammate(name: str, role: str, prompt: str,
                       task_id: str | None = None,
                       require_plan: bool = False) -> str:
    return spawn_teammate_thread(name, role, prompt, task_id, require_plan)


def run_list_teammates() -> str:
    with team_lock:
        if not active_teammates:
            return "No active teammates."
        return "\n".join(
            f"{name}: {status}"
            for name, status in sorted(active_teammates.items())
        )


def run_send_message(to: str, content: str) -> str:
    if to not in active_teammates:
        return f"Teammate '{to}' is not active"
    BUS.send("lead", to, content)
    return f"Sent to {to}"

def run_connect_mcp(name: str) -> str:
    return connect_mcp(name)


# -- Tool Definitions --

# The model sees tool schemas; Python executes handlers. S15 keeps both tables
# explicit so every added capability is visible in one place.
BUILTIN_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object",
                      "properties": {
                          "command": {"type": "string",
                                      "description": "The command line to run."},
                          "run_in_background": {
                              "type": "boolean",
                              "description": ("Start the command without "
                                              "waiting; use for long-running "
                                              "processes such as dev servers.")}},
                      "required": ["command"],
                      "additionalProperties": False}},
    {"name": "read_file",
     "description": (
         "Read a text file. Read a file before editing it, and when you "
         "need its types, props or call sites.\n"
         "path: relative to the workspace root. offset: 0-based line index "
         "to start from (0 = first line). limit: max lines to return; omit "
         "it for files under ~400 lines.\n"
         "Reading node_modules/dist/build is refused (one small .d.ts per "
         "session at most). Re-reading an unchanged file returns a cache "
         "note — that content is already in your context, so make the edit."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "path": {"type": "string",
                                   "description": ("File path relative to the "
                                                   "workspace root.")},
                          "limit": {"type": "integer",
                                    "description": ("Maximum number of lines "
                                                    "to return.")},
                          "offset": {"type": "integer",
                                     "description": ("0-based line index to "
                                                     "start from; 0 is the "
                                                     "first line.")}},
                      "required": ["path"],
                      "additionalProperties": False}},
    {"name": "write_file",
     "description": (
         "Create a new file or replace an existing file's entire contents; "
         "missing parent directories are created.\n"
         "Use edit_file (one change) or apply_patch (several) to modify an "
         "existing file — they rewrite only the fragment you name. Use "
         "write_file only to create a file or rewrite it wholesale."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "path": {"type": "string",
                                   "description": ("File path relative to the "
                                                   "workspace root.")},
                          "content": {"type": "string",
                                      "description": ("The complete new "
                                                      "contents of the file.")}},
                      "required": ["path", "content"],
                      "additionalProperties": False}},
    {"name": "edit_file",
     "description": (
         "Replace one exact text fragment in an existing file — this is the "
         "tool that makes a code change. Read the file first, then copy "
         "old_text verbatim from the output (indentation and quotes "
         "included), with a few neighbouring lines so it matches only the "
         "place you mean.\n"
         "Only the first occurrence is replaced; use apply_patch for "
         "several places or several files. An empty new_text deletes the "
         "fragment. On 'Error: text not found', re-read the file and copy "
         "again — do not guess."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "path": {"type": "string",
                                   "description": ("File path relative to the "
                                                   "workspace root.")},
                          "old_text": {"type": "string",
                                       "description": ("Exact text to find, "
                                                       "copied verbatim from "
                                                       "the current file.")},
                          "new_text": {"type": "string",
                                       "description": ("Replacement text; "
                                                       "empty deletes the "
                                                       "fragment.")}},
                      "required": ["path", "old_text", "new_text"],
                      "additionalProperties": False}},
    {"name": "glob",
     "description": (
         "Find files by name pattern and return their paths. Use it when "
         "you know part of a file name but not its directory, e.g. "
         "'**/selectModel*'.\n"
         "pattern: glob relative to the workspace root; '**' matches nested "
         "directories. Matches inside node_modules/dist/build/.git are "
         "hidden — those trees are not searchable or readable, so use "
         "search_text on the project source to see how a library is used."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "pattern": {"type": "string",
                                      "description": ("Glob relative to the "
                                                      "workspace root, e.g. "
                                                      "'src/**/*.vue'.")}},
                      "required": ["pattern"],
                      "additionalProperties": False}},
    {"name": "list_dir",
     "description": (
         "List one directory's entries: files by name, subdirectories with "
         "a trailing '/', symlinks with '@'. Use it to explore an "
         "unfamiliar directory one level at a time; it works identically on "
         "every platform, unlike 'ls'.\n"
         "Prefer glob when you know part of the file name and search_text "
         "when you know something about its contents."
     ),
     "input_schema": {"type": "object",
                      "properties": {
                          "path": {"type": "string",
                                   "description": ("Directory relative to the "
                                                   "workspace root; default "
                                                   "'.' (the root).")},
                          "max_entries": {"type": "integer",
                                          "description": ("Maximum number of "
                                                          "entries to return.")}},
                      "required": [],
                      "additionalProperties": False}},
    SEARCH_TEXT_TOOL,
    APPLY_PATCH_TOOL,
    {"name": "todo_write",
     "description": (
         "Create and maintain the plan for the current request — this list "
         "is how progress is shown. Call it first, before reading files, "
         "with the whole plan as 3-5 steps, then again as each step starts "
         "or ends.\n"
         "todos: the complete list; it replaces the previous one, so resend "
         "every step. content: one concrete step. status: pending, "
         "in_progress (exactly one) or completed."
     ),
     "input_schema": {"type": "object",
                      "properties": {"todos": {
                          "type": "array",
                          "description": "The complete, ordered task list.",
                          "items": {"type": "object",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": ("One concrete "
                                                            "step of the plan.")},
                                        "status": {"type": "string",
                                                   "enum": ["pending", "in_progress", "completed"],
                                                   "description": ("pending, "
                                                                   "in_progress "
                                                                   "(at most "
                                                                   "one) or "
                                                                   "completed.")}},
                                    "required": ["content", "status"]}}},
                      "required": ["todos"]}},
    {"name": "task",
     "description": (
         "Launch a focused subagent for one self-contained piece of work; "
         "you receive only its final summary, not its transcript. Use it for "
         "independent work that does not touch the files you are editing. "
         "Parameters: description (required) — a complete, self-contained "
         "brief: goal, relevant file paths, and what to return."
     ),
     "input_schema": {"type": "object",
                      "properties": {"description": {
                          "type": "string",
                          "description": ("Self-contained brief: the goal, "
                                          "the files involved, and what the "
                                          "summary should report.")}},
                      "required": ["description"]}},
    {"name": "load_skill",
     "description": (
         "Load the full content of a skill from the skills catalog. Use it "
         "when a catalog entry matches the current request — the returned "
         "text is the workflow to follow. Parameters: name (required), "
         "exactly as listed in the catalog."
     ),
     "input_schema": {"type": "object",
                      "properties": {"name": {
                          "type": "string",
                          "description": ("Skill name as listed in the "
                                          "catalog.")}},
                      "required": ["name"]}},
    {"name": "compact",
     "description": (
         "Summarize the earlier conversation and continue with a shorter "
         "context. Use it only when the conversation has grown very long "
         "and you keep re-reading the same details. Parameters: focus "
         "(optional) — what the summary must preserve."
     ),
     "input_schema": {"type": "object",
                      "properties": {"focus": {
                          "type": "string",
                          "description": ("What the summary must preserve, "
                                          "e.g. 'the two files being "
                                          "changed'.")}},
                      "required": []}},
    {"name": "create_task",
     "description": ("Create a tracked task for work that a teammate or a "
                     "later turn will pick up. Parameters: subject (short "
                     "title), description (what 'done' means), blockedBy "
                     "(ids of tasks that must finish first)."),
     "input_schema": {"type": "object",
                      "properties": {"subject": {"type": "string",
                                                 "description": "Short task title."},
                                     "description": {"type": "string",
                                                     "description": ("What "
                                                                     "'done' "
                                                                     "means "
                                                                     "for this "
                                                                     "task.")},
                                     "blockedBy": {"type": "array",
                                                   "items": {"type": "string"},
                                                   "description": ("Ids of "
                                                                   "tasks that "
                                                                   "must "
                                                                   "complete "
                                                                   "first.")}},
                      "required": ["subject"]}},
    {"name": "list_tasks",
     "description": ("List all tracked tasks with their status. Use it before "
                     "choosing what to work on next."),
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_task",
     "description": ("Show the full details of one task, including its "
                     "description and blockers. Parameters: task_id."),
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string",
                                                 "description": ("Task id as "
                                                                 "shown by "
                                                                 "list_tasks.")}},
                      "required": ["task_id"]}},
    {"name": "claim_task",
     "description": ("Claim a pending task so no one else starts it. "
                     "Parameters: task_id. Claim only tasks you will work on "
                     "now, and complete_task when finished."),
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string",
                                                 "description": ("Task id to "
                                                                 "claim.")}},
                      "required": ["task_id"]}},
    {"name": "complete_task",
     "description": ("Mark a claimed task as done. Parameters: task_id. Call "
                     "it only once the work in the task description is "
                     "actually finished."),
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string",
                                                 "description": ("Task id to "
                                                                 "complete.")}},
                      "required": ["task_id"]}},
    {"name": "schedule_cron",
     "description": ("Schedule work to run later. cron is a 5-field "
                     "expression: minute hour day-of-month month "
                     "day-of-week. For a one-shot reminder, compute the "
                     "target minute/hour/date and set recurring=false. "
                     "Parameters: cron (the expression), prompt (the "
                     "self-contained instruction to run then), recurring, "
                     "durable (survive restarts)."),
     "input_schema": {"type": "object",
                      "properties": {"cron": {"type": "string",
                                              "description": ("5-field cron: "
                                                              "'min hour dom "
                                                              "month dow', "
                                                              "e.g. '30 9 * "
                                                              "* 1-5'.")},
                                     "prompt": {"type": "string",
                                                "description": ("Instruction "
                                                                "to execute "
                                                                "at that time.")},
                                     "recurring": {"type": "boolean",
                                                   "description": ("True to "
                                                                   "repeat; "
                                                                   "false for "
                                                                   "one "
                                                                   "shot.")},
                                     "durable": {"type": "boolean",
                                                 "description": ("True to "
                                                                 "keep the "
                                                                 "job across "
                                                                 "restarts.")}},
                      "required": ["cron", "prompt"]}},
    {"name": "list_crons",
     "description": ("List registered cron jobs with their ids and "
                     "schedules. Use it before cancelling one."),
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "cancel_cron",
     "description": ("Cancel a scheduled job by id (see list_crons). "
                     "Parameters: job_id."),
     "input_schema": {"type": "object",
                      "properties": {"job_id": {"type": "string",
                                                "description": ("Job id from "
                                                                "list_crons.")}},
                      "required": ["job_id"]}},
    {"name": "spawn_teammate",
     "description": ("Spawn a persistent teammate that works in parallel and "
                     "can be messaged. Propose the team to the user and get "
                     "confirmation before calling this. Parameters: name "
                     "(letters, digits, '-' or '_'), role (one-line "
                     "responsibility), prompt (self-contained brief: goal, "
                     "files, expected output), task_id (optional task to "
                     "assign), require_plan (ask it to submit a plan first)."),
     "input_schema": {"type": "object",
                      "properties": {"name": {
                                         "type": "string",
                                         "pattern": "^[A-Za-z0-9_-]{1,64}$",
                                         "description": ("Unique teammate "
                                                         "name."),
                                     },
                                     "role": {"type": "string",
                                              "description": ("One-line "
                                                              "responsibility.")},
                                     "prompt": {"type": "string",
                                                "description": ("Self-contained "
                                                                "brief: goal, "
                                                                "files, "
                                                                "expected "
                                                                "output.")},
                                     "task_id": {
                                         "type": "string",
                                         "pattern": "^task_[0-9a-f]{8}$",
                                         "description": ("Task id to assign, "
                                                         "e.g. task_1a2b3c4d."),
                                     },
                                     "require_plan": {"type": "boolean",
                                                      "description": ("True to "
                                                                      "require a "
                                                                      "plan "
                                                                      "before "
                                                                      "work.")}},
                      "required": ["name", "role", "prompt"]}},
    {"name": "list_teammates",
     "description": ("List active teammates and their status. Use it before "
                     "messaging one, and to check whether work is finished."),
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "send_message",
     "description": ("Send a message to an active teammate (see "
                     "list_teammates). Parameters: to (teammate name), "
                     "content (the message — state what you need, not a "
                     "bare question)."),
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string",
                                             "description": ("Active teammate "
                                                             "name.")},
                                     "content": {"type": "string",
                                                 "description": ("Message "
                                                                 "body.")}},
                      "required": ["to", "content"]}},
    {"name": "request_shutdown",
     "description": ("Ask a teammate to shut down once it has reported its "
                     "final result. Parameters: teammate (name)."),
     "input_schema": {"type": "object",
                      "properties": {"teammate": {"type": "string",
                                                  "description": ("Teammate "
                                                                  "name.")}},
                      "required": ["teammate"]}},
    {"name": "request_plan",
     "description": ("Ask a teammate to submit a plan before it starts "
                     "working. Parameters: teammate (name), task (what it "
                     "should plan for)."),
     "input_schema": {"type": "object",
                      "properties": {"teammate": {"type": "string",
                                                  "description": ("Teammate "
                                                                  "name.")},
                                     "task": {"type": "string",
                                              "description": ("What the plan "
                                                              "should "
                                                              "cover.")}},
                      "required": ["teammate", "task"]}},
    {"name": "review_plan",
     "description": ("Approve or reject a plan a teammate submitted. "
                     "Parameters: request_id (the id of the submitted plan), "
                     "approve (true to start the work), feedback (what to "
                     "change when rejecting)."),
     "input_schema": {"type": "object",
                      "properties": {"request_id": {"type": "string",
                                                    "description": ("Id of the "
                                                                    "submitted "
                                                                    "plan.")},
                                     "approve": {"type": "boolean",
                                                 "description": ("True to "
                                                                 "approve, "
                                                                 "false to "
                                                                 "reject.")},
                                     "feedback": {"type": "string",
                                                  "description": ("Required "
                                                                  "when "
                                                                  "rejecting.")}},
                      "required": ["request_id", "approve"]}},
    {"name": "create_worktree",
     "description": ("Create a git worktree bound to a pending task, so a "
                     "teammate can edit without conflicting with the main "
                     "checkout. Parameters: name, task_id."),
     "input_schema": {"type": "object",
                      "properties": {"name": {
                                         "type": "string",
                                         "pattern": ("^(?!.*\\.\\.)[A-Za-z0-9]"
                                                     "[A-Za-z0-9._-]{0,63}$"),
                                         "maxLength": 64,
                                         "description": ("Worktree directory "
                                                         "name."),
                                     },
                                     "task_id": {"type": "string",
                                                 "description": ("Task id to "
                                                                 "bind the "
                                                                 "worktree "
                                                                 "to.")}},
                      "required": ["name", "task_id"],
                      "additionalProperties": False}},
    {"name": "connect_mcp",
     "description": ("Connect to an MCP server by name (for example docs or "
                     "deploy) and expose its tools for the rest of the "
                     "session. Use it only when the request needs a service "
                     "the built-in tools cannot reach. Parameters: name."),
     "input_schema": {"type": "object",
                      "properties": {"name": {"type": "string",
                                              "description": ("MCP server "
                                                              "name.")}},
                      "required": ["name"]}},
]

def builtin_tools() -> list[dict]:
    """Return tool schemas with host-aware descriptions.

    Rebuilt per round so a description can name the commands this host
    actually has, instead of describing a generic POSIX box.
    """
    tools = [dict(tool) for tool in BUILTIN_TOOLS]
    for tool in tools:
        if tool["name"] == "bash":
            tool["description"] = bash_description()
    return tools


BUILTIN_HANDLERS = {
    "bash": run_agent_bash,
    "read_file": run_agent_read,
    "write_file": run_agent_write,
    "edit_file": run_agent_edit,
    "glob": run_agent_glob,
    "list_dir": run_agent_list_dir,
    "search_text": run_agent_search_text,
    "apply_patch": run_agent_apply_patch,
    "todo_write": run_todo_write, "task": spawn_subagent,
    "load_skill": load_skill,
    "create_task": run_create_task, "list_tasks": run_list_tasks,
    "get_task": run_get_task,
    "claim_task": run_claim_task, "complete_task": run_complete_task,
    "schedule_cron": run_schedule_cron,
    "list_crons": run_list_crons,
    "cancel_cron": run_cancel_cron,
    "spawn_teammate": run_spawn_teammate,
    "list_teammates": run_list_teammates,
    "send_message": run_send_message,
    "request_shutdown": run_request_shutdown,
    "request_plan": run_request_plan, "review_plan": run_review_plan,
    "create_worktree": run_create_worktree,
    "connect_mcp": run_connect_mcp,
}
