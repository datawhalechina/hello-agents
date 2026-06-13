import type { JobItemView } from "../types/research";

export type FollowUpState = "none" | "today" | "overdue" | "upcoming";

const TERMINAL_FOLLOW_UP_STATUSES = new Set(["拒绝", "放弃"]);

export function getLocalDateKey(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function getFollowUpState(
  job: Pick<JobItemView, "applicationStatus" | "nextActionAt">,
  today = getLocalDateKey()
): FollowUpState {
  if (
    !isIsoDate(job.nextActionAt) ||
    TERMINAL_FOLLOW_UP_STATUSES.has(job.applicationStatus || "")
  ) {
    return "none";
  }
  if (job.nextActionAt === today) {
    return "today";
  }
  return job.nextActionAt < today ? "overdue" : "upcoming";
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
