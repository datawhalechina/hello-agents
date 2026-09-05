/**
 * Merge an incoming `todo_list` payload into the current task list by task id.
 *
 * The backend emits the FULL cumulative task list on every `todo_list` event,
 * including the re-planning wave broadcasts. The frontend accumulates rich
 * runtime state (summaries, parsed sources, notices, tool-call logs) from
 * fine-grained events such as `task_status` / `task_summary_chunk` / `tool_call`.
 * Replacing the whole list with freshly-mapped objects would wipe that state
 * for tasks that already ran, so known tasks are merged in place (runtime
 * fields preserved) and only new tasks are appended.
 */
import type { TodoTaskView } from "../types/todo";

export interface IncomingTodoTask {
  id?: unknown;
  title?: unknown;
  intent?: unknown;
  query?: unknown;
  status?: unknown;
  summary?: unknown;
  sources_summary?: unknown;
  note_id?: unknown;
  note_path?: unknown;
}

export interface TodoListMergeOptions {
  fallbackIntent: string;
  fallbackQuery: string;
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function resolveId(item: IncomingTodoTask, index: number): number {
  const raw =
    typeof item.id === "number"
      ? item.id
      : typeof item.id === "string"
        ? Number(item.id)
        : NaN;
  return Number.isFinite(raw) ? raw : index + 1;
}

export function mergeTodoTasks(
  current: TodoTaskView[],
  incoming: IncomingTodoTask[],
  options: TodoListMergeOptions
): TodoTaskView[] {
  const known = new Map(current.map((task) => [task.id, task]));
  const result: TodoTaskView[] = [];

  for (const [index, item] of incoming.entries()) {
    const id = resolveId(item, index);
    const existing = known.get(id);

    if (existing) {
      // Preserve runtime state (summary / sources / notices / tool calls) for
      // tasks we already know; refresh only static metadata when the payload
      // provides a non-empty value.
      result.push({
        ...existing,
        title: optionalString(item.title) ?? existing.title,
        intent: optionalString(item.intent) ?? existing.intent,
        query: optionalString(item.query) ?? existing.query,
        status: optionalString(item.status) ?? existing.status,
        noteId: optionalString(item.note_id) ?? existing.noteId,
        notePath: optionalString(item.note_path) ?? existing.notePath
      });
      continue;
    }

    result.push({
      id,
      title: optionalString(item.title) ?? `任务${id}`,
      intent: optionalString(item.intent) ?? options.fallbackIntent,
      query: optionalString(item.query) ?? options.fallbackQuery,
      status: optionalString(item.status) ?? "pending",
      summary: optionalString(item.summary) ?? "",
      sourcesSummary: optionalString(item.sources_summary) ?? "",
      sourceItems: [],
      notices: [],
      noteId: optionalString(item.note_id),
      notePath: optionalString(item.note_path),
      toolCalls: []
    });
  }

  // Keep any known tasks absent from the incoming snapshot (defensive; the
  // backend currently always sends the full cumulative list).
  const seen = new Set(result.map((task) => task.id));
  for (const task of current) {
    if (!seen.has(task.id)) {
      result.push(task);
    }
  }

  return result;
}
