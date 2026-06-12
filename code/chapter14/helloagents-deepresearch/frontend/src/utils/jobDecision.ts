import type { JobItemView } from "../types/research";

export type SourceTrustLevel = "high" | "medium" | "low";
export type PriorityLevel = "priority" | "normal" | "confirm" | "defer";

export interface JobDecisionMeta {
  sourceTypeLabel: string;
  sourceTrust: SourceTrustLevel;
  sourceTrustLabel: string;
  sourceTrustRank: number;
  sourceTrustReason: string;
  completenessScore: number;
  completenessLabel: string;
  completenessMissing: string[];
  priority: PriorityLevel;
  priorityLabel: string;
  priorityRank: number;
  priorityReason: string;
  confirmationItems: string[];
  hasSourceUrl: boolean;
  riskCount: number;
}

const UNKNOWN_VALUES = new Set(["", "未确认", "暂无可靠信息", "未知"]);

function clean(value: string): string {
  return value.trim();
}

function hasKnownValue(value: string): boolean {
  return !UNKNOWN_VALUES.has(clean(value));
}

function hasKnownList(value: string[]): boolean {
  return value.some((item) => hasKnownValue(item));
}

function isValidUrl(url: string): boolean {
  return /^https?:\/\//.test(url);
}

function getHostname(url: string): string {
  if (!isValidUrl(url)) {
    return "";
  }
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function getSourceText(job: JobItemView): string {
  return `${job.sourceUrl} ${job.sourceTitle}`.toLowerCase();
}

function classifySource(job: JobItemView): Pick<
  JobDecisionMeta,
  "sourceTypeLabel" | "sourceTrust" | "sourceTrustLabel" | "sourceTrustRank" | "sourceTrustReason"
> {
  const sourceText = getSourceText(job);
  const hostname = getHostname(job.sourceUrl);

  if (!isValidUrl(job.sourceUrl)) {
    return {
      sourceTypeLabel: "未知来源",
      sourceTrust: "low",
      sourceTrustLabel: "低可信",
      sourceTrustRank: 1,
      sourceTrustReason: "缺少可打开的来源链接，需要先核验岗位是否真实开放。"
    };
  }

  if (
    hostname.endsWith(".edu.cn") ||
    sourceText.includes("就业") ||
    sourceText.includes("就业网") ||
    sourceText.includes("就业信息")
  ) {
    return {
      sourceTypeLabel: "学校就业网",
      sourceTrust: "high",
      sourceTrustLabel: "高可信",
      sourceTrustRank: 3,
      sourceTrustReason: "来源像学校就业或校招信息页，通常更适合先核验并投递。"
    };
  }

  if (
    sourceText.includes("campus") ||
    sourceText.includes("career") ||
    sourceText.includes("careers") ||
    sourceText.includes("join") ||
    sourceText.includes("talent") ||
    sourceText.includes("校招") ||
    sourceText.includes("招聘官网") ||
    sourceText.includes("社会招聘")
  ) {
    return {
      sourceTypeLabel: "企业/校招官网",
      sourceTrust: "high",
      sourceTrustLabel: "高可信",
      sourceTrustRank: 3,
      sourceTrustReason: "来源像企业招聘或校招官网，投递入口与岗位状态通常更可靠。"
    };
  }

  if (
    sourceText.includes("zhipin") ||
    sourceText.includes("boss直聘") ||
    sourceText.includes("liepin") ||
    sourceText.includes("猎聘") ||
    sourceText.includes("lagou") ||
    sourceText.includes("拉勾") ||
    sourceText.includes("51job") ||
    sourceText.includes("前程无忧") ||
    sourceText.includes("zhaopin") ||
    sourceText.includes("智联") ||
    sourceText.includes("kanzhun")
  ) {
    return {
      sourceTypeLabel: "招聘平台",
      sourceTrust: "medium",
      sourceTrustLabel: "中可信",
      sourceTrustRank: 2,
      sourceTrustReason: "来源像公开招聘平台，适合查看 JD，但仍建议确认投递入口和发布时间。"
    };
  }

  if (
    sourceText.includes("weixin") ||
    sourceText.includes("公众号") ||
    sourceText.includes("mp.weixin") ||
    sourceText.includes("zhihu") ||
    sourceText.includes("小红书")
  ) {
    return {
      sourceTypeLabel: "公众号/内容平台",
      sourceTrust: "medium",
      sourceTrustLabel: "中可信",
      sourceTrustRank: 2,
      sourceTrustReason: "来源像内容平台，可作为线索，但需要继续打开官方入口确认。"
    };
  }

  return {
    sourceTypeLabel: "公开网页",
    sourceTrust: "medium",
    sourceTrustLabel: "中可信",
    sourceTrustRank: 2,
    sourceTrustReason: "来源可打开，但类型不明确，建议核验页面是否为招聘详情页。"
  };
}

function getCompleteness(job: JobItemView): Pick<
  JobDecisionMeta,
  "completenessScore" | "completenessLabel" | "completenessMissing"
> {
  const checks = [
    { label: "公司", ok: hasKnownValue(job.company) },
    { label: "职位", ok: hasKnownValue(job.title) },
    { label: "地点", ok: hasKnownValue(job.location) },
    { label: "来源链接", ok: isValidUrl(job.sourceUrl) },
    { label: "来源标题", ok: hasKnownValue(job.sourceTitle) },
    {
      label: "JD/职责",
      ok: hasKnownList(job.requirements) || hasKnownList(job.responsibilities)
    },
    { label: "技术栈", ok: hasKnownList(job.techStack) },
    { label: "实习周期", ok: hasKnownValue(job.duration) },
    { label: "截止日期", ok: hasKnownValue(job.deadline) }
  ];
  const passed = checks.filter((item) => item.ok).length;
  const completenessScore = Math.round((passed / checks.length) * 100);
  const completenessMissing = checks
    .filter((item) => !item.ok)
    .map((item) => item.label);

  let completenessLabel = "待补全";
  if (completenessScore >= 80) {
    completenessLabel = "信息完整";
  } else if (completenessScore >= 55) {
    completenessLabel = "基本完整";
  }

  return {
    completenessScore,
    completenessLabel,
    completenessMissing
  };
}

function getConfirmationItems(
  job: JobItemView,
  completenessMissing: string[]
): string[] {
  const items: string[] = [];

  if (!isValidUrl(job.sourceUrl)) {
    items.push("缺少可打开来源，先确认岗位来源和投递入口。");
  }
  if (!hasKnownValue(job.location)) {
    items.push("地点未确认，需确认城市、远程或现场要求。");
  }
  if (!hasKnownList(job.requirements) && !hasKnownList(job.responsibilities)) {
    items.push("JD 信息不足，需确认岗位要求与职责。");
  }
  if (!hasKnownValue(job.deadline)) {
    items.push("截止日期未确认，需确认岗位是否仍开放。");
  }
  if (!hasKnownValue(job.duration)) {
    items.push("实习周期未确认，需确认到岗时间和每周出勤。");
  }
  if (completenessMissing.includes("技术栈")) {
    items.push("技术栈不明确，需确认是否匹配当前简历重点。");
  }

  for (const risk of job.risks.filter(hasKnownValue).slice(0, 3)) {
    items.push(`风险提示：${risk}`);
  }

  return Array.from(new Set(items));
}

function getPriority(
  job: JobItemView,
  sourceTrust: SourceTrustLevel,
  sourceTrustRank: number,
  completenessScore: number,
  confirmationItems: string[]
): Pick<
  JobDecisionMeta,
  "priority" | "priorityLabel" | "priorityRank" | "priorityReason"
> {
  const score = job.matchScore ?? 0;
  const riskCount = job.risks.filter(hasKnownValue).length;

  if (
    score < 50 ||
    sourceTrust === "low" ||
    completenessScore < 45 ||
    riskCount >= 3
  ) {
    return {
      priority: "defer",
      priorityLabel: "暂缓",
      priorityRank: 1,
      priorityReason: "匹配分、来源可信度或信息完整度偏弱，建议先核验再决定是否投入时间。"
    };
  }

  if (
    score >= 85 &&
    sourceTrustRank >= 2 &&
    completenessScore >= 70 &&
    confirmationItems.length <= 1
  ) {
    return {
      priority: "priority",
      priorityLabel: "优先投递",
      priorityRank: 4,
      priorityReason: "匹配分较高，来源和信息相对完整，适合优先打开来源确认并人工投递。"
    };
  }

  if (
    score >= 70 &&
    sourceTrustRank >= 2 &&
    completenessScore >= 55 &&
    confirmationItems.length <= 3
  ) {
    return {
      priority: "normal",
      priorityLabel: "可以投递",
      priorityRank: 3,
      priorityReason: "整体条件可用，但仍建议先确认待补全信息后再投递。"
    };
  }

  return {
    priority: "confirm",
    priorityLabel: "待确认",
    priorityRank: 2,
    priorityReason: "岗位线索有价值，但信息还不够完整，需要先补充核验。"
  };
}

export function getJobDecisionMeta(job: JobItemView): JobDecisionMeta {
  const source = classifySource(job);
  const completeness = getCompleteness(job);
  const confirmationItems = getConfirmationItems(
    job,
    completeness.completenessMissing
  );
  const priority = getPriority(
    job,
    source.sourceTrust,
    source.sourceTrustRank,
    completeness.completenessScore,
    confirmationItems
  );

  return {
    ...source,
    ...completeness,
    ...priority,
    confirmationItems,
    hasSourceUrl: isValidUrl(job.sourceUrl),
    riskCount: job.risks.filter(hasKnownValue).length
  };
}
