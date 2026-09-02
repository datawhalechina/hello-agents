/**
 * Regression tests for the task-list merge used by the `todo_list` event
 * handler. See review: the backend re-broadcasts the cumulative task list
 * when re-planning adds follow-up tasks; replacing the list wholesale used to
 * wipe summaries / sources / notices / tool-call history of wave-1 tasks.
 */
import { describe, expect, it } from "vitest";

import { mergeTodoTasks, type IncomingTodoTask } from "./todoMerge";
import type { TodoTaskView } from "../types/todo";

const OPTIONS = {
  fallbackIntent: "默认意图",
  fallbackQuery: "默认查询"
};

function makeTask(id: number, overrides: Partial<TodoTaskView> = {}): TodoTaskView {
  return {
    id,
    title: `任务${id}`,
    intent: "intent",
    query: "query",
    status: "pending",
    summary: "",
    sourcesSummary: "",
    sourceItems: [],
    notices: [],
    noteId: null,
    notePath: null,
    toolCalls: [],
    ...overrides
  };
}

describe("mergeTodoTasks", () => {
  it("preserves wave-1 runtime data when a cumulative wave-2 todo_list arrives", () => {
    const wave1: TodoTaskView[] = [
      makeTask(1, {
        status: "completed",
        summary: "第一波总结",
        sourcesSummary: "来源A",
        sourceItems: [{ title: "A", url: "https://a", snippet: "s", raw: "r" }],
        notices: ["note1"],
        toolCalls: [
          {
            eventId: 1,
            agent: "agent",
            tool: "search",
            parameters: {},
            result: "ok",
            noteId: null,
            notePath: null,
            timestamp: 1
          }
        ]
      })
    ];

    // Wave-2 cumulative snapshot: known task 1 (completed) + new follow-up 2.
    const wave2: IncomingTodoTask[] = [
      { id: 1, title: "框架全景扫描", intent: "i1", query: "q1", status: "completed" },
      { id: 2, title: "补做任务", intent: "i2", query: "q2", status: "pending" }
    ];

    const merged = mergeTodoTasks(wave1, wave2, OPTIONS);

    const task1 = merged.find((task) => task.id === 1);
    expect(task1).toBeDefined();
    expect(task1!.summary).toBe("第一波总结");
    expect(task1!.sourcesSummary).toBe("来源A");
    expect(task1!.sourceItems).toHaveLength(1);
    expect(task1!.notices).toEqual(["note1"]);
    expect(task1!.toolCalls).toHaveLength(1);
    expect(task1!.status).toBe("completed");
    expect(task1!.title).toBe("框架全景扫描"); // static metadata refreshed

    const task2 = merged.find((task) => task.id === 2);
    expect(task2).toBeDefined();
    expect(task2!.status).toBe("pending");
    expect(merged.map((task) => task.id)).toEqual([1, 2]);
  });

  it("creates tasks with fallback metadata when payload fields are missing", () => {
    const merged = mergeTodoTasks([], [{ id: "7" }], OPTIONS);

    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe(7);
    expect(merged[0].title).toBe("任务7");
    expect(merged[0].intent).toBe("默认意图");
    expect(merged[0].status).toBe("pending");
    expect(merged[0].summary).toBe("");
  });

  it("keeps known tasks that are absent from the incoming snapshot", () => {
    const current = [makeTask(1), makeTask(2)];
    const merged = mergeTodoTasks(current, [{ id: 2 }], OPTIONS);

    expect(merged.map((task) => task.id)).toEqual([2, 1]);
  });
});
