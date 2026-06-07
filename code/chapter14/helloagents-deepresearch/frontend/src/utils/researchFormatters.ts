const TASK_STATUS_LABEL: Record<string, string> = {
  pending: "待执行",
  in_progress: "进行中",
  completed: "已完成",
  skipped: "已跳过",
  failed: "失败"
};

export function formatTaskStatus(status: string): string {
  return TASK_STATUS_LABEL[status] ?? status;
}

export function formatMatchScore(score: number | null): string {
  return score === null ? "待确认" : `${score} 分`;
}

export function validJobSourceUrl(url: string): boolean {
  return /^https?:\/\//.test(url);
}

export function formatRejectReason(reason: string): string {
  const labels: Record<string, string> = {
    tutorial_or_blog: "教程/博客",
    interview_noise: "面经/面试",
    not_job_url: "非招聘页",
    missing_jd_terms: "缺少JD特征",
    empty_result: "空结果"
  };
  return labels[reason] ?? reason;
}

export function formatToolParameters(
  parameters: Record<string, unknown>
): string {
  try {
    return JSON.stringify(parameters, null, 2);
  } catch (error) {
    console.warn("无法格式化工具参数", error, parameters);
    return Object.entries(parameters)
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join("\n");
  }
}

export function formatToolResult(result: string): string {
  const trimmed = result.trim();
  const limit = 900;
  if (trimmed.length > limit) {
    return `${trimmed.slice(0, limit)}...`;
  }
  return trimmed;
}
