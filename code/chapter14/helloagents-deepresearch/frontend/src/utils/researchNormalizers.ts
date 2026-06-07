import type {
  JobItemView,
  SearchDiagnosticsView,
  SourceItem
} from "../types/research";

export function extractOptionalString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function ensureRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

export function extractStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => (typeof item === "string" ? item.trim() : ""))
      .filter(Boolean);
  }
  if (typeof value === "string" && value.trim()) {
    return [value.trim()];
  }
  return [];
}

export function extractScore(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return null;
  }
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function extractNumber(value: unknown): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.max(0, Math.round(numberValue)) : 0;
}

export function parseSources(raw: string): SourceItem[] {
  if (!raw) {
    return [];
  }

  const items: SourceItem[] = [];
  const lines = raw.split("\n");

  let current: SourceItem | null = null;
  const truncate = (value: string, max = 360) => {
    const trimmed = value.trim();
    return trimmed.length > max ? `${trimmed.slice(0, max)}...` : trimmed;
  };

  const flush = () => {
    if (!current) {
      return;
    }
    const normalized: SourceItem = {
      title: current.title?.trim() || "",
      url: current.url?.trim() || "",
      snippet: current.snippet ? truncate(current.snippet) : "",
      raw: current.raw ? truncate(current.raw, 420) : ""
    };

    if (
      normalized.title ||
      normalized.url ||
      normalized.snippet ||
      normalized.raw
    ) {
      if (!normalized.title && normalized.url) {
        normalized.title = normalized.url;
      }
      items.push(normalized);
    }
    current = null;
  };

  const ensureCurrent = () => {
    if (!current) {
      current = { title: "", url: "", snippet: "", raw: "" };
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }

    if (/^\*/.test(trimmed) && trimmed.includes(" : ")) {
      flush();
      const withoutBullet = trimmed.replace(/^\*\s*/, "");
      const [titlePart, urlPart] = withoutBullet.split(" : ");
      current = {
        title: titlePart?.trim() || "",
        url: urlPart?.trim() || "",
        snippet: "",
        raw: ""
      };
      continue;
    }

    if (/^(Source|信息来源)\s*:/.test(trimmed)) {
      flush();
      const [, titlePart = ""] = trimmed.split(/:\s*(.+)/);
      current = {
        title: titlePart.trim(),
        url: "",
        snippet: "",
        raw: ""
      };
      continue;
    }

    if (/^URL\s*:/.test(trimmed)) {
      ensureCurrent();
      const [, urlPart = ""] = trimmed.split(/:\s*(.+)/);
      current!.url = urlPart.trim();
      continue;
    }

    if (/^(Most relevant content from source|信息内容)\s*:/.test(trimmed)) {
      ensureCurrent();
      const [, contentPart = ""] = trimmed.split(/:\s*(.+)/);
      current!.snippet = contentPart.trim();
      continue;
    }

    if (/^(Full source content limited to|信息内容限制为)\s*:/.test(trimmed)) {
      ensureCurrent();
      const [, rawPart = ""] = trimmed.split(/:\s*(.+)/);
      current!.raw = rawPart.trim();
      continue;
    }

    if (/^https?:\/\//.test(trimmed)) {
      ensureCurrent();
      if (!current!.url) {
        current!.url = trimmed;
        continue;
      }
    }

    ensureCurrent();
    current!.raw = current!.raw ? `${current!.raw}\n${trimmed}` : trimmed;
  }

  flush();
  return items;
}

export function normalizeSearchDiagnostics(
  value: unknown
): SearchDiagnosticsView | null {
  const item = ensureRecord(value);
  const counts = ensureRecord(item.counts);
  const rejectReasonsRaw = ensureRecord(item.reject_reasons);
  const rejectReasons: Record<string, number> = {};
  for (const [reason, count] of Object.entries(rejectReasonsRaw)) {
    rejectReasons[reason] = extractNumber(count);
  }

  return {
    taskId: extractNumber(item.task_id),
    taskTitle: extractOptionalString(item.task_title) || "岗位搜索",
    backend: extractOptionalString(item.backend) || "unknown",
    query: extractOptionalString(item.query) || "",
    finalQuery: extractOptionalString(item.final_query) || "",
    retryQuery: extractOptionalString(item.retry_query),
    counts: {
      raw: extractNumber(counts.raw),
      reliable: extractNumber(counts.reliable),
      filtered: extractNumber(counts.filtered)
    },
    rejectReasons,
    rejectedSamples: Array.isArray(item.rejected_samples)
      ? item.rejected_samples.map((sample) => {
          const record = ensureRecord(sample);
          return {
            title: extractOptionalString(record.title) || "",
            url: extractOptionalString(record.url) || "",
            reason: extractOptionalString(record.reason) || "unknown"
          };
        })
      : [],
    suggestion:
      extractOptionalString(item.suggestion) ||
      "请调整求职目标或切换搜索引擎后重试。"
  };
}

export function normalizeJobItem(
  value: unknown,
  index: number
): JobItemView | null {
  const item = ensureRecord(value);
  const id =
    extractOptionalString(item.id) ||
    extractOptionalString(item.source_url) ||
    `job-${index + 1}`;
  const title = extractOptionalString(item.title) || "未确认";
  const company = extractOptionalString(item.company) || "未确认";
  const sourceUrl = extractOptionalString(item.source_url) || "";
  const sourceTitle = extractOptionalString(item.source_title) || title;

  if (title === "未确认" && company === "未确认" && !sourceUrl) {
    return null;
  }

  return {
    id,
    company,
    title,
    location: extractOptionalString(item.location) || "未确认",
    sourceUrl,
    sourceTitle,
    requirements: extractStringList(item.requirements),
    responsibilities: extractStringList(item.responsibilities),
    techStack: extractStringList(item.tech_stack),
    duration: extractOptionalString(item.duration) || "未确认",
    deadline: extractOptionalString(item.deadline) || "未确认",
    matchScore: extractScore(item.match_score),
    matchReason:
      extractOptionalString(item.match_reason) || "信息不足，需要打开来源确认",
    resumeAdvice: extractStringList(item.resume_advice),
    risks: extractStringList(item.risks),
    applicationStatus: extractOptionalString(item.application_status),
    statusNote: extractOptionalString(item.status_note) || "",
    savedAt: extractOptionalString(item.saved_at) || "",
    updatedAt: extractOptionalString(item.updated_at) || ""
  };
}

export function normalizeSavedJobItem(
  value: unknown,
  index: number,
  defaultStatus = "待投递"
): JobItemView | null {
  const job = normalizeJobItem(value, index);
  if (!job) {
    return null;
  }
  return {
    ...job,
    applicationStatus: job.applicationStatus || defaultStatus
  };
}
