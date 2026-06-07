import {
  computed,
  onBeforeUnmount,
  reactive,
  ref,
  type Ref
} from "vue";

import {
  runResearchStream,
  StreamInterruptedError,
  type ResearchRequest,
  type ResearchStreamEvent
} from "../services/api";
import type {
  InternshipExample,
  JobItemView,
  ResearchFormState,
  SearchDiagnosticsView,
  StreamStatus,
  TodoTaskView
} from "../types/research";
import {
  ensureRecord,
  extractOptionalString,
  normalizeJobItem,
  normalizeSearchDiagnostics,
  parseSources
} from "../utils/researchNormalizers";

interface ExecuteResearchOptions {
  reset: boolean;
  preserveExisting: boolean;
  allowAutoRetry?: boolean;
}

export function useResearchWorkflow(isExpanded: Ref<boolean>) {
  const form = reactive<ResearchFormState>({
    topic: "",
    searchApi: ""
  });

  const loading = ref(false);
  const error = ref("");
  const streamStatus = ref<StreamStatus>("idle");
  const retryCount = ref(0);
  const maxAutoRetries = 1;
  const lastResearchPayload = ref<ResearchRequest | null>(null);
  const backendStreamErrored = ref(false);
  const preserveExistingResults = ref(false);
  const progressLogs = ref<string[]>([]);
  const logsCollapsed = ref(false);

  const todoTasks = ref<TodoTaskView[]>([]);
  const activeTaskId = ref<number | null>(null);
  const jobItems = ref<JobItemView[]>([]);
  const activeJobId = ref<string | null>(null);
  const searchDiagnostics = ref<SearchDiagnosticsView[]>([]);
  const reportMarkdown = ref("");

  const summaryHighlight = ref(false);
  const sourcesHighlight = ref(false);
  const reportHighlight = ref(false);
  const toolHighlight = ref(false);
  const jobHighlight = ref(false);

  let currentController: AbortController | null = null;
  let userCancelled = false;
  const streamingTaskSummaryIds = new Set<number>();

  const searchOptions = [
    "advanced",
    "duckduckgo",
    "tavily",
    "perplexity",
    "searxng"
  ];

  const internshipExamples: InternshipExample[] = [
    {
      label: "Java 后端实习",
      text: "我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。"
    },
    {
      label: "AI 应用实习",
      text: "我想找 2026 暑期 AI 应用开发实习，城市北京/上海/远程，会 Python、FastAPI、LLM、RAG，有 Agent 项目经验。"
    },
    {
      label: "前端实习",
      text: "我想找 2026 暑期前端开发实习，城市杭州/上海，会 Vue、TypeScript、Vite，做过一个后台管理系统项目。"
    }
  ];

  const totalTasks = computed(() => todoTasks.value.length);
  const completedTasks = computed(() =>
    todoTasks.value.filter((task) => task.status === "completed").length
  );

  const currentTask = computed(() => {
    if (activeTaskId.value !== null) {
      return (
        todoTasks.value.find((task) => task.id === activeTaskId.value) ?? null
      );
    }
    return todoTasks.value[0] ?? null;
  });

  const currentTaskSources = computed(
    () => currentTask.value?.sourceItems ?? []
  );
  const currentTaskSummary = computed(() => currentTask.value?.summary ?? "");
  const currentTaskTitle = computed(() => currentTask.value?.title ?? "");
  const currentTaskIntent = computed(() => currentTask.value?.intent ?? "");
  const currentTaskQuery = computed(() => currentTask.value?.query ?? "");
  const currentTaskSourcesText = computed(
    () => currentTask.value?.sourcesSummary ?? ""
  );
  const currentTaskNoteId = computed(() => currentTask.value?.noteId ?? "");
  const currentTaskNotePath = computed(() => currentTask.value?.notePath ?? "");
  const currentTaskToolCalls = computed(
    () => currentTask.value?.toolCalls ?? []
  );

  const activeJob = computed(() => {
    if (activeJobId.value) {
      return jobItems.value.find((job) => job.id === activeJobId.value) ?? null;
    }
    return jobItems.value[0] ?? null;
  });

  const latestSearchDiagnostics = computed(
    () => searchDiagnostics.value[searchDiagnostics.value.length - 1] ?? null
  );
  const totalDiagnosticCounts = computed(() =>
    searchDiagnostics.value.reduce(
      (acc, item) => {
        acc.raw += item.counts.raw;
        acc.reliable += item.counts.reliable;
        acc.filtered += item.counts.filtered;
        return acc;
      },
      { raw: 0, reliable: 0, filtered: 0 }
    )
  );
  const diagnosticReasonEntries = computed(() => {
    const reasons: Record<string, number> = {};
    for (const item of searchDiagnostics.value) {
      for (const [reason, count] of Object.entries(item.rejectReasons)) {
        reasons[reason] = (reasons[reason] ?? 0) + count;
      }
    }
    return Object.entries(reasons).sort((a, b) => b[1] - a[1]);
  });
  const streamStatusLabel = computed(() => {
    if (streamStatus.value === "retrying") {
      return `连接中断，正在重试 ${retryCount.value}/${maxAutoRetries}`;
    }
    if (streamStatus.value === "interrupted") {
      return "连接中断，可重新尝试";
    }
    if (streamStatus.value === "error") {
      return "找实习流程失败";
    }
    if (streamStatus.value === "cancelled") {
      return "已取消找实习";
    }
    if (loading.value || streamStatus.value === "running") {
      return "正在找实习";
    }
    if (streamStatus.value === "completed") {
      return "找实习流程完成";
    }
    return "找实习流程就绪";
  });
  const canRetryStream = computed(
    () =>
      streamStatus.value === "interrupted" &&
      lastResearchPayload.value !== null &&
      !loading.value
  );

  const pulse = (flag: Ref<boolean>) => {
    flag.value = false;
    requestAnimationFrame(() => {
      flag.value = true;
      window.setTimeout(() => {
        flag.value = false;
      }, 1200);
    });
  };

  function applySearchDiagnosticsPayload(value: unknown, replace = false) {
    if (replace) {
      searchDiagnostics.value = [];
    }

    const values = Array.isArray(value) ? value : [value];
    const parsed = values
      .map((item) => normalizeSearchDiagnostics(item))
      .filter((item): item is SearchDiagnosticsView => Boolean(item));
    if (!parsed.length) {
      return;
    }

    const byTaskId = new Map<number, SearchDiagnosticsView>();
    for (const item of [...searchDiagnostics.value, ...parsed]) {
      byTaskId.set(item.taskId, item);
    }
    searchDiagnostics.value = Array.from(byTaskId.values());
  }

  function mergeJobItems(incoming: JobItemView[]) {
    const seen = new Set<string>();
    const merged: JobItemView[] = [];
    for (const job of [...jobItems.value, ...incoming]) {
      const key = job.sourceUrl || `${job.company}|${job.title}|${job.id}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged.push(job);
    }
    jobItems.value = merged;
    if (!activeJobId.value && merged.length) {
      activeJobId.value = merged[0].id;
    }
  }

  function applyJobPayload(value: unknown, replace = false) {
    if (!Array.isArray(value)) {
      return;
    }
    if (replace) {
      jobItems.value = [];
      activeJobId.value = null;
    }
    const parsed = value
      .map((item, index) => normalizeJobItem(item, index))
      .filter((item): item is JobItemView => Boolean(item));
    if (!parsed.length) {
      return;
    }
    mergeJobItems(parsed);
    pulse(jobHighlight);
  }

  function applyNoteMetadata(
    task: TodoTaskView,
    payload: Record<string, unknown>
  ): void {
    const noteId = extractOptionalString(payload.note_id);
    if (noteId) {
      task.noteId = noteId;
    }
    const notePath = extractOptionalString(payload.note_path);
    if (notePath) {
      task.notePath = notePath;
    }
  }

  function resetWorkflowState() {
    todoTasks.value = [];
    activeTaskId.value = null;
    reportMarkdown.value = "";
    progressLogs.value = [];
    error.value = "";
    streamStatus.value = "idle";
    retryCount.value = 0;
    backendStreamErrored.value = false;
    preserveExistingResults.value = false;
    streamingTaskSummaryIds.clear();
    summaryHighlight.value = false;
    sourcesHighlight.value = false;
    reportHighlight.value = false;
    toolHighlight.value = false;
    jobHighlight.value = false;
    jobItems.value = [];
    activeJobId.value = null;
    searchDiagnostics.value = [];
    logsCollapsed.value = false;
  }

  function findTask(taskId: unknown): TodoTaskView | undefined {
    const numeric =
      typeof taskId === "number"
        ? taskId
        : typeof taskId === "string"
        ? Number(taskId)
        : NaN;
    if (Number.isNaN(numeric)) {
      return undefined;
    }
    return todoTasks.value.find((task) => task.id === numeric);
  }

  function upsertTaskMetadata(
    task: TodoTaskView,
    payload: Record<string, unknown>
  ) {
    if (typeof payload.title === "string" && payload.title.trim()) {
      task.title = payload.title.trim();
    }
    if (typeof payload.intent === "string" && payload.intent.trim()) {
      task.intent = payload.intent.trim();
    }
    if (typeof payload.query === "string" && payload.query.trim()) {
      task.query = payload.query.trim();
    }
  }

  function handleResearchStreamEvent(event: ResearchStreamEvent) {
    if (event.type === "status") {
      const message =
        typeof event.message === "string" && event.message.trim()
          ? event.message
          : "流程状态更新";
      progressLogs.value.push(message);

      const payload = event as Record<string, unknown>;
      const task = findTask(payload.task_id);
      if (task && message) {
        task.notices.push(message);
        applyNoteMetadata(task, payload);
      }
      return;
    }

    if (event.type === "todo_list") {
      const tasks = Array.isArray(event.tasks)
        ? (event.tasks as Record<string, unknown>[])
        : [];

      todoTasks.value = tasks.map((item, index) => {
        const rawId =
          typeof item.id === "number"
            ? item.id
            : typeof item.id === "string"
            ? Number(item.id)
            : index + 1;
        const id = Number.isFinite(rawId) ? Number(rawId) : index + 1;
        const existing = todoTasks.value.find((task) => task.id === id);
        const noteId =
          typeof item.note_id === "string" && item.note_id.trim()
            ? item.note_id.trim()
            : null;
        const notePath =
          typeof item.note_path === "string" && item.note_path.trim()
            ? item.note_path.trim()
            : null;

        return {
          id,
          title:
            typeof item.title === "string" && item.title.trim()
              ? item.title.trim()
              : `任务${id}`,
          intent:
            typeof item.intent === "string" && item.intent.trim()
              ? item.intent.trim()
              : "探索与主题相关的关键信息",
          query:
            typeof item.query === "string" && item.query.trim()
              ? item.query.trim()
              : form.topic.trim(),
          status:
            typeof item.status === "string" && item.status.trim()
              ? item.status.trim()
              : existing?.status ?? "pending",
          summary: existing?.summary ?? "",
          sourcesSummary: existing?.sourcesSummary ?? "",
          sourceItems: existing?.sourceItems ?? [],
          notices: existing?.notices ?? [],
          noteId: noteId ?? existing?.noteId ?? null,
          notePath: notePath ?? existing?.notePath ?? null,
          toolCalls: existing?.toolCalls ?? []
        } as TodoTaskView;
      });

      if (todoTasks.value.length) {
        activeTaskId.value = todoTasks.value[0].id;
        progressLogs.value.push("已生成任务清单");
      } else {
        progressLogs.value.push("未生成任务清单，使用默认任务继续");
      }
      return;
    }

    if (event.type === "task_status") {
      const payload = event as Record<string, unknown>;
      const task = findTask(event.task_id);
      if (!task) {
        return;
      }

      upsertTaskMetadata(task, payload);
      applyNoteMetadata(task, payload);
      const status =
        typeof event.status === "string" && event.status.trim()
          ? event.status.trim()
          : task.status;
      task.status = status;

      if (status === "in_progress") {
        if (!preserveExistingResults.value) {
          task.summary = "";
          task.sourcesSummary = "";
          task.sourceItems = [];
          task.notices = [];
        }
        streamingTaskSummaryIds.delete(task.id);
        activeTaskId.value = task.id;
        progressLogs.value.push(`开始执行任务：${task.title}`);
      } else if (status === "completed") {
        if (typeof event.summary === "string" && event.summary.trim()) {
          task.summary = event.summary.trim();
        }
        if (
          typeof event.sources_summary === "string" &&
          event.sources_summary.trim()
        ) {
          task.sourcesSummary = event.sources_summary.trim();
          task.sourceItems = parseSources(task.sourcesSummary);
        }
        progressLogs.value.push(`完成任务：${task.title}`);
        if (activeTaskId.value === task.id) {
          pulse(summaryHighlight);
          pulse(sourcesHighlight);
        }
      } else if (status === "skipped") {
        progressLogs.value.push(`任务跳过：${task.title}`);
      } else if (status === "failed") {
        const detail =
          typeof event.detail === "string" && event.detail.trim()
            ? `：${event.detail.trim()}`
            : "";
        progressLogs.value.push(`任务失败：${task.title}${detail}`);
      }
      return;
    }

    if (event.type === "sources") {
      const payload = event as Record<string, unknown>;
      const task = findTask(event.task_id);
      if (!task) {
        return;
      }

      const textCandidates = [
        payload.latest_sources,
        payload.sources_summary,
        payload.raw_context
      ];
      const latestText = textCandidates
        .map((value) => (typeof value === "string" ? value.trim() : ""))
        .find((value) => value);

      if (latestText) {
        task.sourcesSummary = latestText;
        task.sourceItems = parseSources(latestText);
        if (activeTaskId.value === task.id) {
          pulse(sourcesHighlight);
        }
        progressLogs.value.push(`已更新任务来源：${task.title}`);
      }

      if (typeof payload.backend === "string") {
        progressLogs.value.push(`当前使用搜索后端：${payload.backend}`);
      }

      applyNoteMetadata(task, payload);

      return;
    }

    if (event.type === "task_summary_chunk") {
      const payload = event as Record<string, unknown>;
      const task = findTask(event.task_id);
      if (!task) {
        return;
      }
      if (
        preserveExistingResults.value &&
        !streamingTaskSummaryIds.has(task.id)
      ) {
        task.summary = "";
        streamingTaskSummaryIds.add(task.id);
      }
      const chunk = typeof event.content === "string" ? event.content : "";
      task.summary += chunk;
      applyNoteMetadata(task, payload);
      if (activeTaskId.value === task.id) {
        pulse(summaryHighlight);
      }
      return;
    }

    if (event.type === "tool_call") {
      const payload = event as Record<string, unknown>;
      const eventId =
        typeof payload.event_id === "number" ? payload.event_id : Date.now();
      const agent =
        typeof payload.agent === "string" && payload.agent.trim()
          ? payload.agent.trim()
          : "Agent";
      const tool =
        typeof payload.tool === "string" && payload.tool.trim()
          ? payload.tool.trim()
          : "tool";
      const parameters = ensureRecord(payload.parameters);
      const result = typeof payload.result === "string" ? payload.result : "";
      const noteId = extractOptionalString(payload.note_id);
      const notePath = extractOptionalString(payload.note_path);

      const task = findTask(payload.task_id);
      if (task) {
        task.toolCalls.push({
          eventId,
          agent,
          tool,
          parameters,
          result,
          noteId,
          notePath,
          timestamp: Date.now()
        });
        if (noteId) {
          task.noteId = noteId;
        }
        if (notePath) {
          task.notePath = notePath;
        }
        const logSummary = noteId
          ? `${agent} 调用了 ${tool}（任务 ${task.id}，笔记 ${noteId}）`
          : `${agent} 调用了 ${tool}（任务 ${task.id}）`;
        progressLogs.value.push(logSummary);
        if (activeTaskId.value === task.id) {
          pulse(toolHighlight);
        }
      } else {
        progressLogs.value.push(`${agent} 调用了 ${tool}`);
      }
      return;
    }

    if (event.type === "search_diagnostics") {
      const payload = event as Record<string, unknown>;
      applySearchDiagnosticsPayload(payload.diagnostics);
      const latest = latestSearchDiagnostics.value;
      if (latest) {
        progressLogs.value.push(
          `搜索诊断：${latest.counts.reliable}/${latest.counts.raw} 个可靠来源`
        );
      }
      return;
    }

    if (event.type === "job_items") {
      const payload = event as Record<string, unknown>;
      applyJobPayload(payload.all_jobs || payload.jobs, Boolean(payload.all_jobs));
      if (jobItems.value.length) {
        progressLogs.value.push(`已更新推荐岗位清单：${jobItems.value.length} 个`);
      }
      return;
    }

    if (event.type === "final_report") {
      const payload = event as Record<string, unknown>;
      applyJobPayload(payload.job_items, true);
      applySearchDiagnosticsPayload(payload.search_diagnostics, true);
      const report =
        typeof event.report === "string" && event.report.trim()
          ? event.report.trim()
          : "";
      reportMarkdown.value = report || "报告生成失败，未获得有效内容";
      pulse(reportHighlight);
      progressLogs.value.push("找实习行动报告已生成");
      return;
    }

    if (event.type === "error") {
      const detail =
        typeof event.detail === "string" && event.detail.trim()
          ? event.detail
          : "找实习过程中发生错误";
      backendStreamErrored.value = true;
      streamStatus.value = "error";
      error.value = detail;
      progressLogs.value.push("找实习流程失败，已停止");
    }
  }

  function isRecoverableStreamError(err: unknown): boolean {
    if (err instanceof StreamInterruptedError) {
      return true;
    }
    if (!(err instanceof TypeError)) {
      return false;
    }
    return /fetch|network|stream|body|terminated|load failed/i.test(
      err.message
    );
  }

  async function executeResearchStream(
    payload: ResearchRequest,
    options: ExecuteResearchOptions
  ) {
    if (currentController) {
      currentController.abort();
      currentController = null;
    }

    if (options.reset) {
      resetWorkflowState();
    }

    loading.value = true;
    error.value = "";
    isExpanded.value = true;
    backendStreamErrored.value = false;
    preserveExistingResults.value = options.preserveExisting;
    streamingTaskSummaryIds.clear();
    streamStatus.value = retryCount.value > 0 ? "retrying" : "running";

    const controller = new AbortController();
    currentController = controller;

    try {
      await runResearchStream(payload, handleResearchStreamEvent, {
        signal: controller.signal
      });

      if (backendStreamErrored.value) {
        return;
      }

      if (!reportMarkdown.value) {
        reportMarkdown.value = "暂无生成的报告";
      }
      streamStatus.value = "completed";
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        if (userCancelled) {
          streamStatus.value = "cancelled";
          progressLogs.value.push("已取消当前找实习任务");
        }
        return;
      }

      if (
        !userCancelled &&
        options.allowAutoRetry !== false &&
        isRecoverableStreamError(err) &&
        retryCount.value < maxAutoRetries
      ) {
        retryCount.value += 1;
        streamStatus.value = "retrying";
        progressLogs.value.push(
          `连接中断，正在自动重试 ${retryCount.value}/${maxAutoRetries}`
        );
        await executeResearchStream(payload, {
          reset: false,
          preserveExisting: true,
          allowAutoRetry: options.allowAutoRetry
        });
        return;
      }

      if (!userCancelled && isRecoverableStreamError(err)) {
        streamStatus.value = "interrupted";
        error.value =
          "连接中断，已保留当前结果，可点击“重新尝试”。";
        progressLogs.value.push(
          "连接中断，当前结果已保留，可手动重新尝试"
        );
        return;
      }

      streamStatus.value = "error";
      error.value = err instanceof Error ? err.message : "请求失败";
    } finally {
      loading.value = false;
      if (currentController === controller) {
        currentController = null;
      }
      preserveExistingResults.value = false;
    }
  }

  const handleSubmit = async () => {
    if (!form.topic.trim()) {
      error.value = "请输入求职目标";
      return;
    }

    userCancelled = false;
    const payload: ResearchRequest = {
      topic: form.topic.trim(),
      search_api: form.searchApi || undefined
    };
    lastResearchPayload.value = payload;
    retryCount.value = 0;

    await executeResearchStream(payload, {
      reset: true,
      preserveExisting: false
    });
  };

  async function retryLastResearch() {
    if (!lastResearchPayload.value || loading.value) {
      return;
    }

    userCancelled = false;
    retryCount.value = 0;
    progressLogs.value.push("正在重新尝试连接找实习流程");
    await executeResearchStream(lastResearchPayload.value, {
      reset: false,
      preserveExisting: true
    });
  }

  const cancelResearch = () => {
    if (!loading.value || !currentController) {
      return;
    }
    userCancelled = true;
    progressLogs.value.push("正在尝试取消当前研究任务...");
    currentController.abort();
  };

  const goBack = () => {
    if (loading.value) {
      return;
    }
    isExpanded.value = false;
  };

  const startNewResearch = () => {
    if (loading.value) {
      cancelResearch();
    }
    resetWorkflowState();
    lastResearchPayload.value = null;
    userCancelled = false;
    isExpanded.value = false;
    form.topic = "";
    form.searchApi = "";
  };

  function fillExample(text: string) {
    if (loading.value) {
      return;
    }
    form.topic = text;
  }

  onBeforeUnmount(() => {
    if (currentController) {
      userCancelled = true;
      currentController.abort();
      currentController = null;
    }
  });

  return {
    activeJob,
    activeJobId,
    activeTaskId,
    canRetryStream,
    cancelResearch,
    completedTasks,
    currentTask,
    currentTaskIntent,
    currentTaskNoteId,
    currentTaskNotePath,
    currentTaskQuery,
    currentTaskSources,
    currentTaskSourcesText,
    currentTaskSummary,
    currentTaskTitle,
    currentTaskToolCalls,
    diagnosticReasonEntries,
    error,
    fillExample,
    form,
    goBack,
    handleSubmit,
    internshipExamples,
    jobHighlight,
    jobItems,
    latestSearchDiagnostics,
    loading,
    logsCollapsed,
    progressLogs,
    pulse,
    reportHighlight,
    reportMarkdown,
    retryLastResearch,
    searchOptions,
    sourcesHighlight,
    startNewResearch,
    streamStatus,
    streamStatusLabel,
    summaryHighlight,
    todoTasks,
    toolHighlight,
    totalDiagnosticCounts,
    totalTasks
  };
}
