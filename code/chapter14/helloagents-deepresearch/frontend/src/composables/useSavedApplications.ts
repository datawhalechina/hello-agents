import { computed, ref, type Ref } from "vue";

import {
  deleteApplication,
  listApplications,
  saveApplication,
  updateApplication,
  type JobApplicationPayload,
  type JobApplicationTrackingField,
  type JobApplicationUpdatePayload
} from "../services/api";
import type { JobItemView } from "../types/research";
import {
  ensureRecord,
  normalizeSavedJobItem
} from "../utils/researchNormalizers";

interface ReadonlyRef<T> {
  readonly value: T;
}

interface UseSavedApplicationsOptions {
  activeJob: ReadonlyRef<JobItemView | null>;
  activeJobId: Ref<string | null>;
  isExpanded: Ref<boolean>;
  jobHighlight: Ref<boolean>;
  jobItems: Ref<JobItemView[]>;
  progressLogs: Ref<string[]>;
  pulse: (flag: Ref<boolean>) => void;
}

export function useSavedApplications(options: UseSavedApplicationsOptions) {
  const savedJobItems = ref<JobItemView[]>([]);
  const applicationStatuses = ref<string[]>([
    "待投递",
    "已投递",
    "笔试",
    "面试",
    "拒绝",
    "Offer",
    "放弃"
  ]);
  const applicationsLoading = ref(false);

  const activeSavedJob = computed(() => {
    if (!options.activeJob.value) {
      return null;
    }
    return findSavedJob(options.activeJob.value);
  });
  const activeJobStatus = computed(
    () =>
      activeSavedJob.value?.applicationStatus || applicationStatuses.value[0]
  );
  const savedApplicationCount = computed(() => savedJobItems.value.length);

  function sameJob(a: JobItemView, b: JobItemView): boolean {
    if (a.sourceUrl && b.sourceUrl) {
      return a.sourceUrl === b.sourceUrl;
    }
    return a.id === b.id;
  }

  function findSavedJob(job: JobItemView): JobItemView | null {
    return savedJobItems.value.find((saved) => sameJob(saved, job)) ?? null;
  }

  function upsertSavedJob(job: JobItemView) {
    savedJobItems.value = [
      job,
      ...savedJobItems.value.filter((saved) => !sameJob(saved, job))
    ];
  }

  function applySavedApplicationsPayload(value: unknown) {
    const payload = ensureRecord(value);
    const statuses = Array.isArray(payload.statuses)
      ? payload.statuses
          .map((status) => (typeof status === "string" ? status.trim() : ""))
          .filter(Boolean)
      : [];
    if (statuses.length) {
      applicationStatuses.value = statuses;
    }

    const items = Array.isArray(payload.job_items) ? payload.job_items : [];
    savedJobItems.value = items
      .map((item, index) =>
        normalizeSavedJobItem(item, index, applicationStatuses.value[0])
      )
      .filter((item): item is JobItemView => Boolean(item));
  }

  function toApplicationPayload(
    job: JobItemView,
    overrides: Partial<JobApplicationPayload> = {}
  ): JobApplicationPayload {
    return {
      id: job.id,
      company: job.company,
      title: job.title,
      location: job.location,
      source_url: job.sourceUrl,
      source_title: job.sourceTitle,
      requirements: job.requirements,
      responsibilities: job.responsibilities,
      tech_stack: job.techStack,
      duration: job.duration,
      deadline: job.deadline,
      match_score: job.matchScore,
      match_reason: job.matchReason,
      resume_advice: job.resumeAdvice,
      risks: job.risks,
      application_status: job.applicationStatus,
      status_note: job.statusNote,
      application_channel: job.applicationChannel,
      applied_at: job.appliedAt,
      next_action: job.nextAction,
      next_action_at: job.nextActionAt,
      resume_version: job.resumeVersion,
      withdrawal_reason: job.withdrawalReason,
      ...overrides
    };
  }

  async function refreshApplications(showLog = false) {
    applicationsLoading.value = true;
    try {
      const payload = await listApplications();
      applySavedApplicationsPayload(payload);
      if (showLog) {
        options.progressLogs.value.push(
          `已刷新保存岗位：${savedApplicationCount.value} 个`
        );
      }
    } catch (error) {
      console.warn("读取保存岗位失败", error);
      if (showLog) {
        options.progressLogs.value.push(
          "读取保存岗位失败，请确认后端已启动"
        );
      }
    } finally {
      applicationsLoading.value = false;
    }
  }

  async function saveJob(job: JobItemView) {
    applicationsLoading.value = true;
    try {
      const saved = await saveApplication(
        toApplicationPayload(job, {
          application_status: undefined,
          status_note: undefined,
          application_channel: undefined,
          applied_at: undefined,
          next_action: undefined,
          next_action_at: undefined,
          resume_version: undefined,
          withdrawal_reason: undefined
        })
      );
      const parsed = normalizeSavedJobItem(
        saved,
        0,
        applicationStatuses.value[0]
      );
      if (parsed) {
        upsertSavedJob(parsed);
        options.progressLogs.value.push(
          `已保存岗位：${parsed.company} · ${parsed.title}`
        );
        options.pulse(options.jobHighlight);
      }
    } catch (error) {
      console.error("保存岗位失败", error);
      options.progressLogs.value.push("保存岗位失败，请稍后重试");
    } finally {
      applicationsLoading.value = false;
    }
  }

  async function saveActiveJob() {
    if (!options.activeJob.value) {
      return;
    }
    await saveJob(options.activeJob.value);
  }

  async function updateSavedJob(
    job: JobItemView,
    patch: JobApplicationUpdatePayload
  ) {
    applicationsLoading.value = true;
    try {
      const updated = await updateApplication(job.id, patch);
      const parsed = normalizeSavedJobItem(
        updated,
        0,
        applicationStatuses.value[0]
      );
      if (parsed) {
        upsertSavedJob(parsed);
        options.progressLogs.value.push(
          `已更新投递状态：${parsed.title}`
        );
      }
    } catch (error) {
      console.error("更新投递状态失败", error);
      options.progressLogs.value.push("更新投递状态失败，请稍后重试");
    } finally {
      applicationsLoading.value = false;
    }
  }

  async function updateSavedJobStatus(job: JobItemView, event: Event) {
    const value = (event.target as HTMLSelectElement | null)?.value;
    if (!value) {
      return;
    }
    await updateSavedJob(job, { application_status: value });
  }

  async function updateActiveJobStatus(event: Event) {
    if (!activeSavedJob.value) {
      return;
    }
    await updateSavedJobStatus(activeSavedJob.value, event);
  }

  async function updateSavedJobNote(job: JobItemView, event: Event) {
    const value = (event.target as HTMLInputElement | null)?.value ?? "";
    await updateSavedJob(job, { status_note: value });
  }

  async function updateActiveJobNote(event: Event) {
    if (!activeSavedJob.value) {
      return;
    }
    await updateSavedJobNote(activeSavedJob.value, event);
  }

  async function updateActiveTrackingField(
    field: JobApplicationTrackingField,
    event: Event
  ) {
    if (!activeSavedJob.value) {
      return;
    }
    const value = (event.target as HTMLInputElement | null)?.value ?? "";
    await updateSavedJob(activeSavedJob.value, { [field]: value });
  }

  async function removeSavedJob(job: JobItemView) {
    applicationsLoading.value = true;
    try {
      await deleteApplication(job.id);
      savedJobItems.value = savedJobItems.value.filter(
        (saved) => saved.id !== job.id
      );
      options.progressLogs.value.push(`已移除保存岗位：${job.title}`);
    } catch (error) {
      console.error("移除保存岗位失败", error);
      options.progressLogs.value.push("移除保存岗位失败，请稍后重试");
    } finally {
      applicationsLoading.value = false;
    }
  }

  async function removeActiveSavedJob() {
    if (!activeSavedJob.value) {
      return;
    }
    await removeSavedJob(activeSavedJob.value);
  }

  function focusSavedJob(job: JobItemView) {
    const existing = options.jobItems.value.find((item) => sameJob(item, job));
    if (existing) {
      options.activeJobId.value = existing.id;
    } else {
      options.jobItems.value = [job, ...options.jobItems.value];
      options.activeJobId.value = job.id;
    }
    options.isExpanded.value = true;
  }

  function openSavedApplications() {
    options.isExpanded.value = true;
    if (savedJobItems.value.length) {
      focusSavedJob(savedJobItems.value[0]);
    }
  }

  return {
    activeJobStatus,
    activeSavedJob,
    applicationStatuses,
    applicationsLoading,
    findSavedJob,
    focusSavedJob,
    openSavedApplications,
    refreshApplications,
    removeActiveSavedJob,
    removeSavedJob,
    saveActiveJob,
    saveJob,
    savedApplicationCount,
    savedJobItems,
    updateActiveJobNote,
    updateActiveJobStatus,
    updateActiveTrackingField,
    updateSavedJobNote,
    updateSavedJobStatus
  };
}
