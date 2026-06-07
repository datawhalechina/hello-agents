<template>
  <section class="job-workbench" :class="{ 'block-highlight': jobHighlight }">
    <div class="block-header">
      <div>
        <h3>推荐岗位清单</h3>
        <p class="muted">
          基于当前求职目标和公开来源抽取，重要信息请点开来源核验。
        </p>
      </div>
      <div class="job-header-actions">
        <span class="job-count">{{ jobItems.length }} 个岗位线索</span>
        <span class="job-count saved">{{ savedApplicationCount }} 个已保存</span>
        <button
          type="button"
          class="secondary-btn compact-btn"
          :disabled="applicationsLoading"
          @click="emit('refresh-applications')"
        >
          刷新保存
        </button>
      </div>
    </div>

    <section v-if="latestSearchDiagnostics" class="diagnostics-panel">
      <div class="diagnostics-head">
        <div>
          <h4>搜索质量诊断</h4>
          <p class="muted">
            {{ latestSearchDiagnostics.backend }} · {{ latestSearchDiagnostics.taskTitle }}
          </p>
        </div>
        <span class="diagnostics-score">
          {{ latestSearchDiagnostics.counts.reliable }} / {{ latestSearchDiagnostics.counts.raw }} 可靠来源
        </span>
      </div>

      <div class="diagnostics-metrics">
        <span>原始结果：{{ totalDiagnosticCounts.raw }}</span>
        <span>可靠岗位：{{ totalDiagnosticCounts.reliable }}</span>
        <span>已过滤：{{ totalDiagnosticCounts.filtered }}</span>
      </div>

      <p class="diagnostics-suggestion">
        {{ latestSearchDiagnostics.suggestion }}
      </p>

      <div v-if="diagnosticReasonEntries.length" class="reason-row">
        <span
          v-for="[reason, count] in diagnosticReasonEntries"
          :key="reason"
        >
          {{ formatRejectReason(reason) }} × {{ count }}
        </span>
      </div>
    </section>

    <div v-if="jobItems.length" class="job-workbench-grid">
      <aside class="job-list" aria-label="推荐岗位列表">
        <button
          v-for="job in jobItems"
          :key="job.id"
          type="button"
          class="job-list-item"
          :class="{ active: activeJobId === job.id }"
          @click="emit('update:activeJobId', job.id)"
        >
          <span class="job-list-title">{{ job.title }}</span>
          <span class="job-list-meta">
            {{ job.company }} · {{ job.location }}
          </span>
          <span
            class="score-badge"
            :class="{ pending: job.matchScore === null }"
          >
            {{ formatMatchScore(job.matchScore) }}
          </span>
          <span v-if="findSavedJob(job)" class="application-badge">
            {{ findSavedJob(job)?.applicationStatus }}
          </span>
        </button>
      </aside>

      <article class="job-detail" v-if="activeJob">
        <header class="job-detail-head">
          <div>
            <h4>{{ activeJob.title }}</h4>
            <p class="muted">
              {{ activeJob.company }} · {{ activeJob.location }}
            </p>
          </div>
          <span
            class="score-badge large"
            :class="{ pending: activeJob.matchScore === null }"
          >
            {{ formatMatchScore(activeJob.matchScore) }}
          </span>
        </header>

        <section class="application-panel">
          <div class="application-panel-head">
            <div>
              <h5>投递跟踪</h5>
              <p class="muted">
                {{ activeSavedJob ? "此岗位已加入本地跟踪清单。" : "保存后可以维护投递阶段和备注。" }}
              </p>
            </div>
            <div class="application-actions">
              <button
                type="button"
                class="secondary-btn compact-btn"
                :disabled="applicationsLoading"
                @click="emit('save-active-job')"
              >
                {{ activeSavedJob ? "更新保存" : "保存岗位" }}
              </button>
              <button
                v-if="activeSavedJob"
                type="button"
                class="secondary-btn compact-btn danger"
                :disabled="applicationsLoading"
                @click="emit('remove-active-saved-job')"
              >
                移除
              </button>
            </div>
          </div>

          <div v-if="activeSavedJob" class="application-controls">
            <label>
              <span>投递状态</span>
              <select
                :value="activeJobStatus"
                :disabled="applicationsLoading"
                @change="emit('update-active-job-status', $event)"
              >
                <option
                  v-for="status in applicationStatuses"
                  :key="status"
                  :value="status"
                >
                  {{ status }}
                </option>
              </select>
            </label>
            <label class="application-note-field">
              <span>备注</span>
              <input
                :value="activeSavedJob.statusNote"
                :disabled="applicationsLoading"
                placeholder="例如：已找学长内推、周三一面"
                @change="emit('update-active-job-note', $event)"
              />
            </label>
          </div>
        </section>

        <div class="job-facts">
          <span>实习周期：{{ activeJob.duration }}</span>
          <span>截止日期：{{ activeJob.deadline }}</span>
          <a
            v-if="validJobSourceUrl(activeJob.sourceUrl)"
            :href="activeJob.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
          >
            查看来源：{{ activeJob.sourceTitle }}
          </a>
          <span v-else>来源：未确认</span>
        </div>

        <section class="job-detail-section">
          <h5>JD要求</h5>
          <ul v-if="activeJob.requirements.length">
            <li v-for="item in activeJob.requirements" :key="item">
              {{ item }}
            </li>
          </ul>
          <p v-else class="muted">暂无可靠信息</p>
        </section>

        <section class="job-detail-section">
          <h5>岗位职责</h5>
          <ul v-if="activeJob.responsibilities.length">
            <li v-for="item in activeJob.responsibilities" :key="item">
              {{ item }}
            </li>
          </ul>
          <p v-else class="muted">暂无可靠信息</p>
        </section>

        <section class="job-detail-section">
          <h5>技术栈</h5>
          <div v-if="activeJob.techStack.length" class="tag-row">
            <span v-for="item in activeJob.techStack" :key="item">
              {{ item }}
            </span>
          </div>
          <p v-else class="muted">暂无可靠信息</p>
        </section>

        <section class="job-detail-section">
          <h5>匹配理由</h5>
          <p>{{ activeJob.matchReason }}</p>
        </section>

        <section class="job-detail-section">
          <h5>简历建议</h5>
          <ul v-if="activeJob.resumeAdvice.length">
            <li v-for="item in activeJob.resumeAdvice" :key="item">
              {{ item }}
            </li>
          </ul>
          <p v-else class="muted">暂无可靠信息</p>
        </section>

        <section class="job-detail-section">
          <h5>风险与待确认</h5>
          <ul v-if="activeJob.risks.length">
            <li v-for="item in activeJob.risks" :key="item">
              {{ item }}
            </li>
          </ul>
          <p v-else class="muted">暂无可靠信息</p>
        </section>
      </article>
    </div>

    <p v-else-if="!savedJobItems.length" class="muted job-empty">
      暂未找到可靠岗位/JD链接。{{ latestSearchDiagnostics?.suggestion || "请调整求职目标或切换搜索引擎后重试。" }}
    </p>

    <section v-if="savedJobItems.length" class="saved-jobs-panel">
      <div class="saved-jobs-head">
        <div>
          <h4>已保存岗位</h4>
          <p class="muted">
            本地保存的投递跟踪清单，刷新页面后仍会保留。
          </p>
        </div>
        <span class="job-count saved">{{ savedApplicationCount }} 个</span>
      </div>

      <ul class="saved-jobs-list">
        <li v-for="job in savedJobItems" :key="job.id">
          <button
            type="button"
            class="saved-job-main"
            @click="emit('focus-saved-job', job)"
          >
            <span class="saved-job-title">{{ job.title }}</span>
            <span class="saved-job-meta">
              {{ job.company }} · {{ job.location }}
            </span>
          </button>
          <select
            class="saved-job-status"
            :value="job.applicationStatus || applicationStatuses[0]"
            :disabled="applicationsLoading"
            @change="emit('update-saved-job-status', job, $event)"
          >
            <option
              v-for="status in applicationStatuses"
              :key="status"
              :value="status"
            >
              {{ status }}
            </option>
          </select>
          <input
            class="saved-job-note"
            :value="job.statusNote"
            :disabled="applicationsLoading"
            placeholder="备注"
            @change="emit('update-saved-job-note', job, $event)"
          />
          <button
            type="button"
            class="secondary-btn compact-btn danger"
            :disabled="applicationsLoading"
            @click="emit('remove-saved-job', job)"
          >
            移除
          </button>
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import type {
  JobItemView,
  SearchDiagnosticsView
} from "../types/research";
import {
  formatMatchScore,
  formatRejectReason,
  validJobSourceUrl
} from "../utils/researchFormatters";

defineProps<{
  activeJob: JobItemView | null;
  activeJobId: string | null;
  activeJobStatus: string;
  activeSavedJob: JobItemView | null;
  applicationStatuses: string[];
  applicationsLoading: boolean;
  diagnosticReasonEntries: Array<[string, number]>;
  findSavedJob: (job: JobItemView) => JobItemView | null;
  jobHighlight: boolean;
  jobItems: JobItemView[];
  latestSearchDiagnostics: SearchDiagnosticsView | null;
  savedApplicationCount: number;
  savedJobItems: JobItemView[];
  totalDiagnosticCounts: {
    raw: number;
    reliable: number;
    filtered: number;
  };
}>();

const emit = defineEmits<{
  "focus-saved-job": [job: JobItemView];
  "refresh-applications": [];
  "remove-active-saved-job": [];
  "remove-saved-job": [job: JobItemView];
  "save-active-job": [];
  "update-active-job-note": [event: Event];
  "update-active-job-status": [event: Event];
  "update-saved-job-note": [job: JobItemView, event: Event];
  "update-saved-job-status": [job: JobItemView, event: Event];
  "update:activeJobId": [value: string];
}>();
</script>

<style scoped>
.job-workbench {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.job-workbench h3 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.job-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.job-count {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(191, 219, 254, 0.32);
  border: 1px solid rgba(59, 130, 246, 0.28);
  color: #1e3a8a;
  font-size: 12px;
  font-weight: 600;
}

.job-count.saved,
.application-badge {
  background: rgba(220, 252, 231, 0.58);
  border-color: rgba(34, 197, 94, 0.28);
  color: #15803d;
}

.diagnostics-panel {
  padding: 16px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 16px;
  background: rgba(239, 246, 255, 0.62);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diagnostics-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.diagnostics-head h4 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1f2937;
}

.diagnostics-score {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.diagnostics-metrics,
.reason-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.diagnostics-metrics span,
.reason-row span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.diagnostics-suggestion {
  margin: 0;
  color: #1f2937;
  line-height: 1.7;
}

.job-workbench-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 18px;
  align-items: start;
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.job-list-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 10px;
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.86);
  color: #1f2937;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.job-list-item.active,
.job-list-item:hover {
  border-color: rgba(59, 130, 246, 0.42);
  background: rgba(219, 234, 254, 0.5);
}

.job-list-title {
  grid-column: 1 / -1;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.45;
}

.job-list-meta {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.score-badge {
  align-self: start;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.16);
  color: #15803d;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.score-badge.pending {
  background: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.score-badge.large {
  padding: 7px 12px;
  font-size: 13px;
}

.application-badge {
  align-self: start;
  padding: 4px 9px;
  border: 1px solid rgba(34, 197, 94, 0.28);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.job-detail {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  padding: 18px;
  background: rgba(248, 250, 252, 0.82);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.job-detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.job-detail h4,
.job-detail h5 {
  margin: 0;
  color: #1f2937;
}

.job-detail h4 {
  font-size: 18px;
  font-weight: 700;
}

.job-detail h5 {
  font-size: 14px;
  font-weight: 700;
}

.application-panel {
  padding: 14px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 14px;
  background: rgba(239, 246, 255, 0.62);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.application-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.application-panel h5,
.application-panel p {
  margin: 0;
}

.application-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.application-controls {
  display: grid;
  grid-template-columns: minmax(140px, 180px) minmax(220px, 1fr);
  gap: 10px;
}

.application-controls label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.application-controls select,
.application-controls input,
.saved-job-status,
.saved-job-note {
  width: 100%;
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  color: #1f2937;
  font-size: 13px;
  padding: 8px 10px;
  box-sizing: border-box;
}

.job-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.job-facts span,
.job-facts a {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #475569;
  font-size: 12px;
  text-decoration: none;
}

.job-facts a {
  color: #2563eb;
  font-weight: 600;
}

.job-detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.job-detail-section p {
  margin: 0;
  color: #1f2937;
  line-height: 1.7;
}

.job-detail-section ul {
  margin: 0 0 0 18px;
  padding: 0;
  color: #1f2937;
  line-height: 1.7;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(219, 234, 254, 0.7);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.job-empty {
  margin: 0;
  padding: 14px;
  border: 1px dashed rgba(148, 163, 184, 0.45);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.7);
}

.saved-jobs-panel {
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.saved-jobs-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.saved-jobs-head h4 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #1f2937;
}

.saved-jobs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.saved-jobs-list li {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) minmax(112px, 140px) minmax(180px, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.78);
}

.saved-job-main {
  min-width: 0;
  border: none;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.saved-job-title,
.saved-job-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.saved-job-title {
  color: #1f2937;
  font-size: 14px;
  font-weight: 700;
}

.saved-job-meta {
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 960px) {
  .job-workbench-grid {
    grid-template-columns: 1fr;
  }

  .application-controls,
  .saved-jobs-list li {
    grid-template-columns: 1fr;
  }
}
</style>
