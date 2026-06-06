<template>
  <main class="app-shell" :class="{ expanded: isExpanded }">
    <div class="aurora" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <!-- 初始状态：居中输入卡片 -->
    <div v-if="!isExpanded" class="layout layout-centered">
      <section class="panel panel-form panel-centered">
        <header class="panel-head">
          <div class="logo">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 2.5c-.7 0-1.4.2-2 .6L4.6 7C3.6 7.6 3 8.7 3 9.9v4.2c0 1.2.6 2.3 1.6 2.9l5.4 3.9c1.2.8 2.8.8 4 0l5.4-3.9c1-.7 1.6-1.7 1.6-2.9V9.9c0-1.2-.6-2.3-1.6-2.9L14 3.1a3.6 3.6 0 0 0-2-.6Z"
              />
            </svg>
          </div>
          <div>
            <h1>找实习助手</h1>
            <p>搜索岗位和投递渠道，分析 JD 要求，生成可执行的投递建议。</p>
          </div>
        </header>

        <form class="form" @submit.prevent="handleSubmit">
          <label class="field">
            <span>求职目标</span>
            <textarea
              v-model="form.topic"
              placeholder="例如：我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。"
              rows="4"
              required
            ></textarea>
          </label>

          <section class="example-prompts" aria-label="求职目标示例">
            <button
              v-for="example in internshipExamples"
              :key="example.label"
              type="button"
              class="example-chip"
              :disabled="loading"
              @click="fillExample(example.text)"
            >
              {{ example.label }}
            </button>
          </section>

          <section class="options">
            <label class="field option">
              <span>搜索引擎</span>
              <select v-model="form.searchApi">
                <option value="">沿用后端配置</option>
                <option
                  v-for="option in searchOptions"
                  :key="option"
                  :value="option"
                >
                  {{ option }}
                </option>
              </select>
            </label>
          </section>

          <div class="form-actions">
            <button class="submit" type="submit" :disabled="loading">
              <span class="submit-label">
                <svg
                  v-if="loading"
                  class="spinner"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="9" stroke-width="3" />
                </svg>
                {{ loading ? "正在找实习..." : "开始找实习" }}
              </span>
            </button>
            <button
              v-if="loading"
              type="button"
              class="secondary-btn"
              @click="cancelResearch"
            >
              取消找实习
            </button>
          </div>
        </form>

        <section v-if="savedJobItems.length" class="saved-jobs-home">
          <div>
            <h2>已保存岗位</h2>
            <p class="muted">{{ savedApplicationCount }} 个岗位正在跟踪</p>
          </div>
          <button
            type="button"
            class="secondary-btn compact-btn"
            @click="openSavedApplications"
          >
            查看清单
          </button>
        </section>

        <p v-if="error" class="error-chip">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path
              d="M10 3.2c-.3 0-.6.2-.8.5L3.4 15c-.4.7.1 1.6.8 1.6h11.6c.7 0 1.2-.9.8-1.6L10.8 3.7c-.2-.3-.5-.5-.8-.5Zm0 4.3c.4 0 .7.3.7.7v4c0 .4-.3.7-.7.7s-.7-.3-.7-.7V8.2c0-.4.3-.7.7-.7Zm0 6.6a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
            />
          </svg>
          {{ error }}
        </p>
        <p v-else-if="loading" class="hint muted">
          正在收集岗位、JD 和投递渠道线索，实时进展见右侧区域。
        </p>
      </section>
    </div>

    <!-- 全屏状态：左右分栏布局 -->
    <div v-else class="layout layout-fullscreen">
      <!-- 左侧：求职信息 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <button class="back-btn" @click="goBack" :disabled="loading">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M19 12H5M12 19l-7-7 7-7" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <h2>找实习助手</h2>
        </div>

        <div class="research-info">
          <div class="info-item">
            <label>求职目标</label>
            <p class="topic-display">{{ form.topic }}</p>
          </div>

          <div class="info-item" v-if="form.searchApi">
            <label>搜索引擎</label>
            <p>{{ form.searchApi }}</p>
          </div>

          <div class="info-item" v-if="totalTasks > 0">
            <label>找实习进度</label>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${(completedTasks / totalTasks) * 100}%` }"></div>
            </div>
            <p class="progress-text">{{ completedTasks }} / {{ totalTasks }} 任务完成</p>
          </div>
        </div>

        <div class="sidebar-actions">
          <button class="new-research-btn" @click="startNewResearch">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
            </svg>
            开始新的求职分析
          </button>
        </div>
      </aside>

      <!-- 右侧：求职分析结果 -->
      <section
        class="panel panel-result"
        v-if="todoTasks.length || reportMarkdown || progressLogs.length || savedJobItems.length"
      >
        <header class="status-bar">
          <div class="status-main">
            <div
              class="status-chip"
              :class="{
                active: loading,
                warning: streamStatus === 'retrying' || streamStatus === 'interrupted',
                failed: streamStatus === 'error'
              }"
            >
              <span class="dot"></span>
              {{ streamStatusLabel }}
            </div>
            <span class="status-meta">
              任务进度：{{ completedTasks }} / {{ totalTasks || todoTasks.length || 1 }}
              · 阶段记录 {{ progressLogs.length }} 条
            </span>
          </div>
          <div class="status-controls">
            <button
              v-if="canRetryStream"
              type="button"
              class="secondary-btn"
              @click="retryLastResearch"
            >
              重新尝试
            </button>
            <button class="secondary-btn" @click="logsCollapsed = !logsCollapsed">
              {{ logsCollapsed ? "展开流程" : "收起流程" }}
            </button>
          </div>
        </header>

        <div class="timeline-wrapper" v-show="!logsCollapsed && progressLogs.length">
          <transition-group name="timeline" tag="ul" class="timeline">
            <li v-for="(log, index) in progressLogs" :key="`${log}-${index}`">
              <span class="timeline-node"></span>
              <p>{{ log }}</p>
            </li>
          </transition-group>
        </div>

        <section
          class="job-workbench"
          :class="{ 'block-highlight': jobHighlight }"
          v-if="jobItems.length || savedJobItems.length || (!loading && (todoTasks.length || reportMarkdown))"
        >
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
                @click="refreshApplications(true)"
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
                @click="activeJobId = job.id"
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
                <span
                  v-if="findSavedJob(job)"
                  class="application-badge"
                >
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
                      @click="saveActiveJob"
                    >
                      {{ activeSavedJob ? "更新保存" : "保存岗位" }}
                    </button>
                    <button
                      v-if="activeSavedJob"
                      type="button"
                      class="secondary-btn compact-btn danger"
                      :disabled="applicationsLoading"
                      @click="removeActiveSavedJob"
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
                      @change="updateActiveJobStatus"
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
                      @change="updateActiveJobNote"
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
                  @click="focusSavedJob(job)"
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
                  @change="updateSavedJobStatus(job, $event)"
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
                  @change="updateSavedJobNote(job, $event)"
                />
                <button
                  type="button"
                  class="secondary-btn compact-btn danger"
                  :disabled="applicationsLoading"
                  @click="removeSavedJob(job)"
                >
                  移除
                </button>
              </li>
            </ul>
          </section>
        </section>

        <div class="tasks-section" v-if="todoTasks.length">
          <aside class="tasks-list">
            <h3>任务清单</h3>
            <ul>
              <li
                v-for="task in todoTasks"
                :key="task.id"
                :class="['task-item', { active: task.id === activeTaskId, completed: task.status === 'completed' }]"
              >
                <button
                  type="button"
                  class="task-button"
                  @click="activeTaskId = task.id"
                >
                  <span class="task-title">{{ task.title }}</span>
                  <span class="task-status" :class="task.status">
                    {{ formatTaskStatus(task.status) }}
                  </span>
                </button>
                <p class="task-intent">{{ task.intent }}</p>
              </li>
            </ul>
          </aside>

          <article class="task-detail" v-if="currentTask">
            <header class="task-header">
              <div>
                <h3>{{ currentTaskTitle || "当前任务" }}</h3>
                <p class="muted" v-if="currentTaskIntent">
                  {{ currentTaskIntent }}
                </p>
              </div>
              <div class="task-chip-group">
                <span class="task-label">查询：{{ currentTaskQuery || "" }}</span>
                <span
                  v-if="currentTaskNoteId"
                  class="task-label note-chip"
                  :title="currentTaskNoteId"
                >
                  笔记：{{ currentTaskNoteId }}
                </span>
                <span
                  v-if="currentTaskNotePath"
                  class="task-label note-chip path-chip"
                  :title="currentTaskNotePath"
                >
                  <span class="path-label">路径：</span>
                  <span class="path-text">{{ currentTaskNotePath }}</span>
                  <button
                    class="chip-action"
                    type="button"
                    @click="copyNotePath(currentTaskNotePath)"
                  >
                    复制
                  </button>
                </span>
              </div>
            </header>

            <section v-if="currentTask && currentTask.notices.length" class="task-notices">
              <h4>系统提示</h4>
              <ul>
                <li v-for="(notice, idx) in currentTask.notices" :key="`${notice}-${idx}`">
                  {{ notice }}
                </li>
              </ul>
            </section>

            <section
              class="sources-block"
              :class="{ 'block-highlight': sourcesHighlight }"
            >
              <div class="block-header">
                <h3>岗位/JD/渠道来源</h3>
                <button
                  type="button"
                  class="secondary-btn compact-btn"
                  :disabled="!currentTaskSourcesText"
                  @click="copyCurrentTaskSources"
                >
                  复制当前来源
                </button>
              </div>
              <template v-if="currentTaskSources.length">
                <ul class="sources-list">
                  <li
                    v-for="(item, index) in currentTaskSources"
                    :key="`${item.title}-${index}`"
                    class="source-item"
                  >
                    <a
                      class="source-link"
                      :href="item.url || '#'"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ item.title || item.url || `来源 ${index + 1}` }}
                    </a>
                    <div v-if="item.snippet || item.raw" class="source-tooltip">
                      <p v-if="item.snippet">{{ item.snippet }}</p>
                      <p v-if="item.raw" class="muted-text">{{ item.raw }}</p>
                    </div>
                  </li>
                </ul>
              </template>
              <p v-else class="muted">暂无岗位/JD/渠道来源，可以调整求职目标或切换搜索引擎后重试。</p>
            </section>

            <section
              class="summary-block"
              :class="{ 'block-highlight': summaryHighlight }"
            >
              <h3>岗位分析</h3>
              <pre class="block-pre">{{ currentTaskSummary || "暂无可用信息" }}</pre>
            </section>

            <section
              class="tools-block"
              :class="{ 'block-highlight': toolHighlight }"
              v-if="currentTaskToolCalls.length"
            >
              <h3>工具调用记录</h3>
              <ul class="tool-list">
                <li
                  v-for="entry in currentTaskToolCalls"
                  :key="`${entry.eventId}-${entry.timestamp}`"
                  class="tool-entry"
                >
                  <div class="tool-entry-header">
                    <span class="tool-entry-title">
                      #{{ entry.eventId }} {{ entry.agent }} → {{ entry.tool }}
                    </span>
                    <span
                      v-if="entry.noteId"
                      class="tool-entry-note"
                    >
                      笔记：{{ entry.noteId }}
                    </span>
                  </div>
                  <p v-if="entry.notePath" class="tool-entry-path">
                    笔记路径：
                    <button
                      class="link-btn"
                      type="button"
                      @click="copyNotePath(entry.notePath)"
                    >
                      复制
                    </button>
                    <span class="path-text">{{ entry.notePath }}</span>
                  </p>
                  <p class="tool-subtitle">参数</p>
                  <pre class="tool-pre">{{ formatToolParameters(entry.parameters) }}</pre>
                  <template v-if="entry.result">
                    <p class="tool-subtitle">执行结果</p>
                    <pre class="tool-pre">{{ formatToolResult(entry.result) }}</pre>
                  </template>
                </li>
              </ul>
            </section>
          </article>

          <article class="task-detail" v-else>
            <p class="muted">等待任务规划或执行结果。</p>
          </article>
        </div>

        <div
          v-if="reportMarkdown"
          class="report-block"
          :class="{ 'block-highlight': reportHighlight }"
        >
          <div class="block-header">
            <h3>找实习行动报告</h3>
            <button
              type="button"
              class="secondary-btn compact-btn"
              :disabled="!reportMarkdown"
              @click="copyReport"
            >
              复制报告
            </button>
          </div>
          <pre class="block-pre">{{ reportMarkdown }}</pre>
        </div>
      </section>

    </div>
  </main>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
  deleteApplication,
  listApplications,
  runResearchStream,
  saveApplication,
  StreamInterruptedError,
  updateApplication,
  type JobApplicationPayload,
  type ResearchRequest,
  type ResearchStreamEvent
} from "./services/api";

interface SourceItem {
  title: string;
  url: string;
  snippet: string;
  raw: string;
}

interface ToolCallLog {
  eventId: number;
  agent: string;
  tool: string;
  parameters: Record<string, unknown>;
  result: string;
  noteId: string | null;
  notePath: string | null;
  timestamp: number;
}

interface TodoTaskView {
  id: number;
  title: string;
  intent: string;
  query: string;
  status: string;
  summary: string;
  sourcesSummary: string;
  sourceItems: SourceItem[];
  notices: string[];
  noteId: string | null;
  notePath: string | null;
  toolCalls: ToolCallLog[];
}

interface JobItemView {
  id: string;
  company: string;
  title: string;
  location: string;
  sourceUrl: string;
  sourceTitle: string;
  requirements: string[];
  responsibilities: string[];
  techStack: string[];
  duration: string;
  deadline: string;
  matchScore: number | null;
  matchReason: string;
  resumeAdvice: string[];
  risks: string[];
  applicationStatus: string | null;
  statusNote: string;
  savedAt: string;
  updatedAt: string;
}

interface SearchDiagnosticsView {
  taskId: number;
  taskTitle: string;
  backend: string;
  query: string;
  finalQuery: string;
  retryQuery: string | null;
  counts: {
    raw: number;
    reliable: number;
    filtered: number;
  };
  rejectReasons: Record<string, number>;
  rejectedSamples: Array<{
    title: string;
    url: string;
    reason: string;
  }>;
  suggestion: string;
}

type StreamStatus =
  | "idle"
  | "running"
  | "retrying"
  | "interrupted"
  | "completed"
  | "error"
  | "cancelled";

const form = reactive({
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
const isExpanded = ref(false);

const todoTasks = ref<TodoTaskView[]>([]);
const activeTaskId = ref<number | null>(null);
const jobItems = ref<JobItemView[]>([]);
const activeJobId = ref<string | null>(null);
const searchDiagnostics = ref<SearchDiagnosticsView[]>([]);
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

const internshipExamples = [
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

const TASK_STATUS_LABEL: Record<string, string> = {
  pending: "待执行",
  in_progress: "进行中",
  completed: "已完成",
  skipped: "已跳过",
  failed: "失败"
};

function formatTaskStatus(status: string): string {
  return TASK_STATUS_LABEL[status] ?? status;
}

const totalTasks = computed(() => todoTasks.value.length);
const completedTasks = computed(() =>
  todoTasks.value.filter((task) => task.status === "completed").length
);

const currentTask = computed(() => {
  if (activeTaskId.value !== null) {
    return todoTasks.value.find((task) => task.id === activeTaskId.value) ?? null;
  }
  return todoTasks.value[0] ?? null;
});

const currentTaskSources = computed(() => currentTask.value?.sourceItems ?? []);
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
const activeSavedJob = computed(() => {
  if (!activeJob.value) {
    return null;
  }
  return findSavedJob(activeJob.value);
});
const activeJobStatus = computed(
  () => activeSavedJob.value?.applicationStatus || applicationStatuses.value[0]
);
const savedApplicationCount = computed(() => savedJobItems.value.length);
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

const pulse = (flag: typeof summaryHighlight) => {
  flag.value = false;
  requestAnimationFrame(() => {
    flag.value = true;
    window.setTimeout(() => {
      flag.value = false;
    }, 1200);
  });
};

function parseSources(raw: string): SourceItem[] {
  if (!raw) {
    return [];
  }

  const items: SourceItem[] = [];
  const lines = raw.split("\n");

  let current: SourceItem | null = null;
  const truncate = (value: string, max = 360) => {
    const trimmed = value.trim();
    return trimmed.length > max ? `${trimmed.slice(0, max)}…` : trimmed;
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

    if (
      /^(Most relevant content from source|信息内容)\s*:/.test(trimmed)
    ) {
      ensureCurrent();
      const [, contentPart = ""] = trimmed.split(/:\s*(.+)/);
      current!.snippet = contentPart.trim();
      continue;
    }

    if (
      /^(Full source content limited to|信息内容限制为)\s*:/.test(trimmed)
    ) {
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

function extractOptionalString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function ensureRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function extractStringList(value: unknown): string[] {
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

function extractScore(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return null;
  }
  return Math.max(0, Math.min(100, Math.round(score)));
}

function extractNumber(value: unknown): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.max(0, Math.round(numberValue)) : 0;
}

function normalizeSearchDiagnostics(value: unknown): SearchDiagnosticsView | null {
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

function formatRejectReason(reason: string): string {
  const labels: Record<string, string> = {
    tutorial_or_blog: "教程/博客",
    interview_noise: "面经/面试",
    not_job_url: "非招聘页",
    missing_jd_terms: "缺少JD特征",
    empty_result: "空结果"
  };
  return labels[reason] ?? reason;
}

function normalizeJobItem(value: unknown, index: number): JobItemView | null {
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
      extractOptionalString(item.match_reason) || "信息不足，需点开来源确认",
    resumeAdvice: extractStringList(item.resume_advice),
    risks: extractStringList(item.risks),
    applicationStatus: extractOptionalString(item.application_status),
    statusNote: extractOptionalString(item.status_note) || "",
    savedAt: extractOptionalString(item.saved_at) || "",
    updatedAt: extractOptionalString(item.updated_at) || ""
  };
}

function normalizeSavedJobItem(value: unknown, index: number): JobItemView | null {
  const job = normalizeJobItem(value, index);
  if (!job) {
    return null;
  }
  return {
    ...job,
    applicationStatus: job.applicationStatus || applicationStatuses.value[0]
  };
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
    .map((item, index) => normalizeSavedJobItem(item, index))
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
    ...overrides
  };
}

async function refreshApplications(showLog = false) {
  applicationsLoading.value = true;
  try {
    const payload = await listApplications();
    applySavedApplicationsPayload(payload);
    if (showLog) {
      progressLogs.value.push(`已刷新保存岗位：${savedApplicationCount.value} 个`);
    }
  } catch (error) {
    console.warn("读取保存岗位失败", error);
    if (showLog) {
      progressLogs.value.push("读取保存岗位失败，请确认后端已启动");
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
        status_note: undefined
      })
    );
    const parsed = normalizeSavedJobItem(saved, 0);
    if (parsed) {
      upsertSavedJob(parsed);
      progressLogs.value.push(`已保存岗位：${parsed.company} · ${parsed.title}`);
      pulse(jobHighlight);
    }
  } catch (error) {
    console.error("保存岗位失败", error);
    progressLogs.value.push("保存岗位失败，请稍后重试");
  } finally {
    applicationsLoading.value = false;
  }
}

async function saveActiveJob() {
  if (!activeJob.value) {
    return;
  }
  await saveJob(activeJob.value);
}

async function updateSavedJob(
  job: JobItemView,
  patch: Pick<JobApplicationPayload, "application_status" | "status_note">
) {
  applicationsLoading.value = true;
  try {
    const updated = await updateApplication(job.id, patch);
    const parsed = normalizeSavedJobItem(updated, 0);
    if (parsed) {
      upsertSavedJob(parsed);
      progressLogs.value.push(`已更新投递状态：${parsed.title}`);
    }
  } catch (error) {
    console.error("更新投递状态失败", error);
    progressLogs.value.push("更新投递状态失败，请稍后重试");
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

async function removeSavedJob(job: JobItemView) {
  applicationsLoading.value = true;
  try {
    await deleteApplication(job.id);
    savedJobItems.value = savedJobItems.value.filter((saved) => saved.id !== job.id);
    progressLogs.value.push(`已移除保存岗位：${job.title}`);
  } catch (error) {
    console.error("移除保存岗位失败", error);
    progressLogs.value.push("移除保存岗位失败，请稍后重试");
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
  const existing = jobItems.value.find((item) => sameJob(item, job));
  if (existing) {
    activeJobId.value = existing.id;
  } else {
    jobItems.value = [job, ...jobItems.value];
    activeJobId.value = job.id;
  }
  isExpanded.value = true;
}

function openSavedApplications() {
  isExpanded.value = true;
  if (savedJobItems.value.length) {
    focusSavedJob(savedJobItems.value[0]);
  }
}

function formatMatchScore(score: number | null): string {
  return score === null ? "待确认" : `${score} 分`;
}

function validJobSourceUrl(url: string): boolean {
  return /^https?:\/\//.test(url);
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

function formatToolParameters(parameters: Record<string, unknown>): string {
  try {
    return JSON.stringify(parameters, null, 2);
  } catch (error) {
    console.warn("无法格式化工具参数", error, parameters);
    return Object.entries(parameters)
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join("\n");
  }
}

function formatToolResult(result: string): string {
  const trimmed = result.trim();
  const limit = 900;
  if (trimmed.length > limit) {
    return `${trimmed.slice(0, limit)}…`;
  }
  return trimmed;
}

async function copyNotePath(path: string | null | undefined) {
  if (!path) {
    return;
  }

  await copyText(path, `已复制笔记路径：${path}`, "复制以下笔记路径");
}

async function copyReport() {
  await copyText(reportMarkdown.value, "已复制找实习行动报告", "复制以下报告内容");
}

async function copyCurrentTaskSources() {
  const title = currentTaskTitle.value || "当前任务";
  await copyText(
    currentTaskSourcesText.value,
    `已复制来源：${title}`,
    "复制以下来源内容"
  );
}

async function copyText(text: string | null | undefined, successLog: string, promptTitle: string) {
  if (!text) {
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    progressLogs.value.push(successLog);
  } catch (error) {
    console.warn("无法直接复制到剪贴板", error);
    window.prompt(promptTitle, text);
    progressLogs.value.push("请手动复制内容");
  }
}

function fillExample(text: string) {
  if (loading.value) {
    return;
  }
  form.topic = text;
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

function upsertTaskMetadata(task: TodoTaskView, payload: Record<string, unknown>) {
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
  return /fetch|network|stream|body|terminated|load failed/i.test(err.message);
}

interface ExecuteResearchOptions {
  reset: boolean;
  preserveExisting: boolean;
  allowAutoRetry?: boolean;
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
      error.value = "连接中断，已保留当前结果，可点击“重新尝试”。";
      progressLogs.value.push("连接中断，当前结果已保留，可手动重新尝试");
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
  progressLogs.value.push("正在尝试取消当前研究任务…");
  currentController.abort();
};

const goBack = () => {
  if (loading.value) {
    return; // 找实习流程进行中不允许返回
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

onMounted(() => {
  void refreshApplications();
});

onBeforeUnmount(() => {
  if (currentController) {
    userCancelled = true;
    currentController.abort();
    currentController = null;
  }
});
</script>


<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  padding: 72px 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at 20% 20%, #f8fafc, #dbeafe 60%);
  color: #1f2937;
  overflow: hidden;
  box-sizing: border-box;
  transition: padding 0.4s ease;
}

.app-shell.expanded {
  padding: 0;
  align-items: stretch;
}

.aurora {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.55;
}

.aurora span {
  position: absolute;
  width: 45vw;
  height: 45vw;
  max-width: 520px;
  max-height: 520px;
  background: radial-gradient(circle, rgba(148, 197, 255, 0.35), transparent 60%);
  filter: blur(90px);
  animation: float 26s infinite linear;
}

.aurora span:nth-child(1) {
  top: -20%;
  left: -18%;
  animation-delay: 0s;
}

.aurora span:nth-child(2) {
  bottom: -25%;
  right: -20%;
  background: radial-gradient(circle, rgba(166, 139, 255, 0.28), transparent 60%);
  animation-delay: -9s;
}

.aurora span:nth-child(3) {
  top: 35%;
  left: 45%;
  background: radial-gradient(circle, rgba(164, 219, 216, 0.26), transparent 60%);
  animation-delay: -16s;
}

.layout {
  position: relative;
  width: 100%;
  display: flex;
  gap: 24px;
  z-index: 1;
  transition: all 0.4s ease;
}

.layout-centered {
  max-width: 600px;
  justify-content: center;
  align-items: center;
}

.layout-fullscreen {
  height: 100vh;
  max-width: 100%;
  gap: 0;
  align-items: stretch;
}

.panel {
  position: relative;
  flex: 1 1 360px;
  padding: 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.panel-form {
  max-width: 420px;
}

.panel-centered {
  width: 100%;
  max-width: 600px;
  padding: 40px;
  box-shadow: 0 32px 64px rgba(15, 23, 42, 0.15);
  transform: scale(1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.panel-centered:hover {
  transform: scale(1.02);
  box-shadow: 0 40px 80px rgba(15, 23, 42, 0.2);
}

.panel-result {
  min-width: 360px;
  flex: 2 1 420px;
}

.panel::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(125, 86, 255, 0.1));
  opacity: 0;
  transition: opacity 0.35s ease;
  z-index: 0;
}

.panel:hover::before {
  opacity: 1;
}

.panel > * {
  position: relative;
  z-index: 1;
}

.panel-form h1 {
  margin: 0;
  font-size: 26px;
  letter-spacing: 0.01em;
}

.panel-form p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.logo {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.4);
}

.logo svg {
  width: 28px;
  height: 28px;
  fill: #f8fafc;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field span {
  font-weight: 600;
  color: #475569;
}

.example-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-chip {
  border: 1px solid rgba(59, 130, 246, 0.28);
  background: rgba(219, 234, 254, 0.45);
  color: #1e40af;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.example-chip:hover:not(:disabled) {
  background: rgba(191, 219, 254, 0.72);
  border-color: rgba(37, 99, 235, 0.45);
  transform: translateY(-1px);
}

.example-chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

textarea,
input,
select {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2937;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

textarea:focus,
input:focus,
select:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.65);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  background: #ffffff;
}

.options {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.option {
  flex: 1;
  min-width: 140px;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.submit {
  align-self: flex-start;
  padding: 12px 24px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.submit-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.submit .spinner {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.85);
  stroke-linecap: round;
  animation: spin 1s linear infinite;
}

.submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.submit:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
}

.secondary-btn {
  padding: 10px 18px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.secondary-btn:hover {
  background: rgba(148, 163, 184, 0.2);
  border-color: rgba(148, 163, 184, 0.35);
  color: #0f172a;
}

.secondary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.compact-btn {
  padding: 7px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.secondary-btn.danger {
  border-color: rgba(248, 113, 113, 0.35);
  background: rgba(254, 226, 226, 0.55);
  color: #b91c1c;
}

.secondary-btn.danger:hover {
  border-color: rgba(239, 68, 68, 0.48);
  background: rgba(254, 202, 202, 0.68);
}

.error-chip {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 14px;
  color: #b91c1c;
  font-size: 14px;
}

.error-chip svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.panel-result {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.status-controls {
  display: flex;
  gap: 8px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(191, 219, 254, 0.28);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  color: #1f2937;
  border: 1px solid rgba(59, 130, 246, 0.35);
  transition: background 0.3s ease, color 0.3s ease;
}

.status-chip.active {
  background: rgba(129, 140, 248, 0.2);
  border-color: rgba(129, 140, 248, 0.4);
  color: #1e293b;
}

.status-chip.warning {
  background: rgba(254, 243, 199, 0.62);
  border-color: rgba(245, 158, 11, 0.38);
  color: #92400e;
}

.status-chip.failed {
  background: rgba(254, 226, 226, 0.7);
  border-color: rgba(239, 68, 68, 0.42);
  color: #991b1b;
}

.status-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 12px rgba(37, 99, 235, 0.45);
  animation: pulse 1.8s ease-in-out infinite;
}

.status-chip.warning .dot {
  background: #d97706;
  box-shadow: 0 0 12px rgba(217, 119, 6, 0.36);
}

.status-chip.failed .dot {
  background: #dc2626;
  box-shadow: 0 0 12px rgba(220, 38, 38, 0.36);
}

.status-meta {
  color: #64748b;
  font-size: 13px;
}

.timeline-wrapper {
  margin-top: 12px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(129, 140, 248, 0.45) rgba(226, 232, 240, 0.6);
}

.timeline-wrapper::-webkit-scrollbar {
  width: 6px;
}

.timeline-wrapper::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.6);
  border-radius: 999px;
}

.timeline-wrapper::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(129, 140, 248, 0.8), rgba(59, 130, 246, 0.7));
  border-radius: 999px;
}

.timeline-wrapper::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.9), rgba(37, 99, 235, 0.8));
}

.timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  padding-left: 12px;
}

.timeline::before {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 0;
  width: 2px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.35), rgba(129, 140, 248, 0.15));
}

.timeline li {
  position: relative;
  padding-left: 24px;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.5;
}

.timeline-node {
  position: absolute;
  left: -12px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #38bdf8, #7c3aed);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.22);
}

.timeline-enter-active,
.timeline-leave-active {
  transition: all 0.35s ease, opacity 0.35s ease;
}

.timeline-enter-from,
.timeline-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

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

.saved-jobs-home {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.78);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.saved-jobs-home h2 {
  margin: 0 0 4px;
  font-size: 15px;
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

.tasks-section {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 960px) {
  .job-workbench-grid {
    grid-template-columns: 1fr;
  }

  .application-controls,
  .saved-jobs-list li {
    grid-template-columns: 1fr;
  }

  .tasks-section {
    grid-template-columns: 1fr;
  }
}

.tasks-list {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.4);
}

.tasks-list h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.tasks-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  border-radius: 14px;
  border: 1px solid transparent;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.task-item.completed {
  border-color: rgba(56, 189, 248, 0.35);
  background: rgba(191, 219, 254, 0.28);
}

.task-item.active {
  border-color: rgba(129, 140, 248, 0.5);
  background: rgba(224, 231, 255, 0.5);
}

.task-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px 6px;
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.task-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.task-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
  background: rgba(148, 163, 184, 0.2);
}

.task-status.pending {
  background: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.task-status.in_progress {
  background: rgba(129, 140, 248, 0.24);
  color: #312e81;
}

.task-status.completed {
  background: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.task-status.skipped {
  background: rgba(248, 113, 113, 0.18);
  color: #b91c1c;
}

.task-status.failed {
  background: rgba(239, 68, 68, 0.18);
  color: #991b1b;
}

.task-intent {
  margin: 0;
  padding: 0 14px 12px 14px;
  font-size: 13px;
  color: #64748b;
}

.task-detail {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.5);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}

.task-chip-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.task-header .muted {
  margin: 6px 0 0;
}

.task-label {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(191, 219, 254, 0.32);
  border: 1px solid rgba(59, 130, 246, 0.35);
  font-size: 12px;
  color: #1e3a8a;
}

.task-label.note-chip {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.35);
  color: #15803d;
}

.task-label.path-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 360px;
  background: rgba(56, 189, 248, 0.2);
  border-color: rgba(56, 189, 248, 0.35);
  color: #0369a1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-label {
  font-weight: 500;
}

.path-text {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-action {
  border: none;
  background: rgba(56, 189, 248, 0.2);
  color: #0369a1;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.chip-action:hover {
  background: rgba(14, 165, 233, 0.28);
  color: #0f172a;
}

.task-notices {
  background: rgba(191, 219, 254, 0.28);
  border: 1px solid rgba(96, 165, 250, 0.35);
  border-radius: 16px;
  padding: 14px 18px;
  color: #1f2937;
}

.task-notices h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.task-notices ul {
  list-style: disc;
  margin: 0 0 0 18px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-notices li {
  font-size: 13px;
}

.report-block {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-block h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.block-header h3 {
  margin: 0;
}

.block-pre {
  font-family: "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular,
    Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: #1f2937;
  background: rgba(248, 250, 252, 0.9);
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  overflow: auto;
  max-height: 420px;
  scrollbar-width: thin;
  scrollbar-color: rgba(129, 140, 248, 0.6) rgba(226, 232, 240, 0.7);
}

.block-pre::-webkit-scrollbar {
  width: 6px;
}

.block-pre::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.7);
  border-radius: 999px;
}

.block-pre::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.75), rgba(59, 130, 246, 0.65));
  border-radius: 999px;
}

.block-pre::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(79, 70, 229, 0.8), rgba(37, 99, 235, 0.75));
}

.summary-block .block-pre,
.sources-block .block-pre {
  max-height: 360px;
}


.tools-block {
  position: relative;
  margin-top: 16px;
  padding: 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.4);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tools-block h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.02em;
}

.tool-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-entry {
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-entry-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.tool-entry-title {
  font-weight: 600;
  color: #1f2937;
}

.tool-entry-note {
  font-size: 12px;
  color: #0f766e;
}

.tool-entry-path {
  margin: 0;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
}

.tool-subtitle {
  margin: 0;
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.tool-pre {
  font-family: "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular,
    Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #1f2937;
  background: rgba(248, 250, 252, 0.9);
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  overflow: auto;
  max-height: 260px;
  scrollbar-width: thin;
  scrollbar-color: rgba(129, 140, 248, 0.6) rgba(226, 232, 240, 0.7);
}

.tool-pre::-webkit-scrollbar {
  width: 6px;
}

.tool-pre::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.7);
}

.tool-pre::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.7);
  border-radius: 10px;
}

.link-btn {
  background: none;
  border: none;
  color: #0369a1;
  cursor: pointer;
  padding: 0 4px;
  font-size: 12px;
  border-radius: 8px;
  transition: color 0.2s ease, background 0.2s ease;
}

.link-btn:hover {
  color: #0ea5e9;
  background: rgba(14, 165, 233, 0.16);
}


.sources-block,
.summary-block {
  position: relative;
  margin-top: 16px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.4);
}

.sources-history {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sources-history h4 {
  margin: 0;
  color: #1f2937;
  font-size: 14px;
  letter-spacing: 0.01em;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-list details {
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  padding: 12px 16px;
  color: #1f2937;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.history-list details[open] {
  background: rgba(224, 231, 255, 0.55);
  border-color: rgba(129, 140, 248, 0.4);
}

.history-list summary {
  cursor: pointer;
  font-weight: 600;
  outline: none;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-list summary::-webkit-details-marker {
  display: none;
}

.history-list summary::after {
  content: "▾";
  margin-left: 6px;
  font-size: 12px;
  opacity: 0.7;
  transition: transform 0.2s ease;
}

.history-list details[open] summary::after {
  transform: rotate(180deg);
}

.block-highlight {
  animation: glow 1.2s ease;
}

.sources-block h3,
.summary-block h3 {
  margin: 0 0 14px;
  color: #1f2937;
  letter-spacing: 0.02em;
}

.sources-block .block-header h3,
.report-block .block-header h3 {
  margin: 0;
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
}

.source-link {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
  letter-spacing: 0.01em;
  transition: color 0.2s ease;
}

.source-link::after {
  content: " ↗";
  font-size: 12px;
  opacity: 0.6;
}

.source-link:hover {
  color: #0f172a;
}

.source-tooltip {
  display: none;
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.98);
  color: #1f2937;
  padding: 14px 16px;
  border-radius: 16px;
  box-shadow: 0 18px 32px rgba(15, 23, 42, 0.18);
  width: min(420px, 90vw);
  z-index: 20;
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.source-tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-width: 10px;
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.98) transparent transparent transparent;
}

.source-tooltip::before {
  content: "";
  position: absolute;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 12px 10px 0 10px;
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.98) transparent transparent transparent;
  filter: drop-shadow(0 -2px 4px rgba(15, 23, 42, 0.12));
}

.source-tooltip p {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.6;
}

.source-tooltip p:last-child {
  margin-bottom: 0;
}

.muted-text {
  color: #64748b;
}

.source-item:hover .source-tooltip,
.source-item:focus-within .source-tooltip {
  display: block;
}

.hint.muted {
  color: #64748b;
}

@keyframes float {
  0% {
    transform: translate3d(0, 0, 0) rotate(0deg);
  }
  50% {
    transform: translate3d(10%, 6%, 0) rotate(3deg);
  }
  100% {
    transform: translate3d(0, 0, 0) rotate(0deg);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.5;
  }
}

@keyframes glow {
  0% {
    box-shadow: 0 0 0 rgba(59, 130, 246, 0.3);
    border-color: rgba(59, 130, 246, 0.5);
  }
  100% {
    box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.12);
    border-color: rgba(148, 163, 184, 0.2);
  }
}

@media (max-width: 960px) {
  .app-shell {
    padding: 56px 16px;
  }

  .layout {
    flex-direction: column;
    align-items: stretch;
  }

  .panel {
    padding: 22px;
  }

  .panel-form,
  .panel-result {
    max-width: none;
  }

  .status-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-main,
  .status-controls {
    width: 100%;
  }

  .status-controls {
    justify-content: flex-start;
  }
}

@media (max-width: 600px) {
  .options {
    flex-direction: column;
  }

  .status-meta {
    font-size: 12px;
  }

  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-form h1 {
    font-size: 24px;
  }
}

/* 侧边栏样式 */
.sidebar {
  width: 400px;
  min-width: 400px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.98);
  border-right: 1px solid rgba(148, 163, 184, 0.2);
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.08);
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: #1f2937;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: transparent;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  width: fit-content;
}

.back-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
  color: #3b82f6;
}

.back-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.research-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
}

.info-item p {
  margin: 0;
  font-size: 14px;
  color: #1f2937;
  line-height: 1.6;
}

.topic-display {
  font-size: 16px !important;
  font-weight: 600;
  color: #0f172a !important;
  padding: 12px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  border-left: 3px solid #3b82f6;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 13px !important;
  color: #64748b !important;
  font-weight: 500;
}

.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.new-research-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.new-research-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.new-research-btn:active {
  transform: translateY(0);
}

/* 全屏状态下的结果面板 */
.layout-fullscreen .panel-result {
  flex: 1;
  height: 100vh;
  border-radius: 0;
  border: none;
  overflow-y: auto;
  max-width: none;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 320px;
    min-width: 320px;
  }
}

@media (max-width: 768px) {
  .layout-fullscreen {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    min-width: 100%;
    height: auto;
    max-height: 40vh;
  }

  .layout-fullscreen .panel-result {
    height: 60vh;
  }
}
</style>
