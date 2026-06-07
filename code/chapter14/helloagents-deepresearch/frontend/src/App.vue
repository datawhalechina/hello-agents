<template>
  <main class="app-shell" :class="{ expanded: isExpanded }">
    <div class="aurora" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <div v-if="!isExpanded" class="layout layout-centered">
      <HomePanel
        :error="error"
        :form="form"
        :internship-examples="internshipExamples"
        :loading="loading"
        :saved-application-count="savedApplicationCount"
        :saved-job-items="savedJobItems"
        :search-options="searchOptions"
        @cancel="cancelResearch"
        @fill-example="fillExample"
        @open-saved-applications="openSavedApplications"
        @submit="handleSubmit"
      />
    </div>

    <div v-else class="layout layout-fullscreen">
      <ResearchSidebar
        :completed-tasks="completedTasks"
        :form="form"
        :loading="loading"
        :total-tasks="totalTasks"
        @back="goBack"
        @start-new="startNewResearch"
      />

      <section
        class="panel panel-result"
        v-if="todoTasks.length || reportMarkdown || progressLogs.length || savedJobItems.length"
      >
        <StatusTimeline
          :can-retry-stream="canRetryStream"
          :completed-tasks="completedTasks"
          :loading="loading"
          :logs-collapsed="logsCollapsed"
          :progress-logs="progressLogs"
          :stream-status="streamStatus"
          :stream-status-label="streamStatusLabel"
          :todo-tasks-length="todoTasks.length"
          :total-tasks="totalTasks"
          @retry="retryLastResearch"
          @toggle-logs="logsCollapsed = !logsCollapsed"
        />

        <JobWorkbench
          v-if="jobItems.length || savedJobItems.length || (!loading && (todoTasks.length || reportMarkdown))"
          v-model:active-job-id="activeJobId"
          :active-job="activeJob"
          :active-job-status="activeJobStatus"
          :active-saved-job="activeSavedJob"
          :application-statuses="applicationStatuses"
          :applications-loading="applicationsLoading"
          :diagnostic-reason-entries="diagnosticReasonEntries"
          :find-saved-job="findSavedJob"
          :job-highlight="jobHighlight"
          :job-items="jobItems"
          :latest-search-diagnostics="latestSearchDiagnostics"
          :saved-application-count="savedApplicationCount"
          :saved-job-items="savedJobItems"
          :total-diagnostic-counts="totalDiagnosticCounts"
          @focus-saved-job="focusSavedJob"
          @refresh-applications="refreshApplications(true)"
          @remove-active-saved-job="removeActiveSavedJob"
          @remove-saved-job="removeSavedJob"
          @save-active-job="saveActiveJob"
          @update-active-job-note="updateActiveJobNote"
          @update-active-job-status="updateActiveJobStatus"
          @update-saved-job-note="updateSavedJobNote"
          @update-saved-job-status="updateSavedJobStatus"
        />

        <TaskWorkspace
          v-model:active-task-id="activeTaskId"
          :current-task="currentTask"
          :current-task-intent="currentTaskIntent"
          :current-task-note-id="currentTaskNoteId"
          :current-task-note-path="currentTaskNotePath"
          :current-task-query="currentTaskQuery"
          :current-task-sources="currentTaskSources"
          :current-task-sources-text="currentTaskSourcesText"
          :current-task-summary="currentTaskSummary"
          :current-task-title="currentTaskTitle"
          :current-task-tool-calls="currentTaskToolCalls"
          :sources-highlight="sourcesHighlight"
          :summary-highlight="summaryHighlight"
          :todo-tasks="todoTasks"
          :tool-highlight="toolHighlight"
          @copy-current-task-sources="copyCurrentTaskSources"
          @copy-note-path="copyNotePath"
        />

        <ReportBlock
          v-if="reportMarkdown"
          :report-highlight="reportHighlight"
          :report-markdown="reportMarkdown"
          @copy-report="copyReport"
        />
      </section>
    </div>
  </main>
</template>

<script lang="ts" setup>
import { onMounted, ref } from "vue";

import HomePanel from "./components/HomePanel.vue";
import JobWorkbench from "./components/JobWorkbench.vue";
import ReportBlock from "./components/ReportBlock.vue";
import ResearchSidebar from "./components/ResearchSidebar.vue";
import StatusTimeline from "./components/StatusTimeline.vue";
import TaskWorkspace from "./components/TaskWorkspace.vue";
import { useClipboardActions } from "./composables/useClipboardActions";
import { useResearchWorkflow } from "./composables/useResearchWorkflow";
import { useSavedApplications } from "./composables/useSavedApplications";

const isExpanded = ref(false);

const {
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
} = useResearchWorkflow(isExpanded);

const {
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
  savedApplicationCount,
  savedJobItems,
  updateActiveJobNote,
  updateActiveJobStatus,
  updateSavedJobNote,
  updateSavedJobStatus
} = useSavedApplications({
  activeJob,
  activeJobId,
  isExpanded,
  jobHighlight,
  jobItems,
  progressLogs,
  pulse
});

const { copyCurrentTaskSources, copyNotePath, copyReport } =
  useClipboardActions({
    currentTaskSourcesText,
    currentTaskTitle,
    progressLogs,
    reportMarkdown
  });

onMounted(() => {
  void refreshApplications();
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

.panel-result {
  min-width: 360px;
  flex: 2 1 420px;
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.layout-fullscreen .panel-result {
  flex: 1;
  height: 100vh;
  border-radius: 0;
  border: none;
  overflow-y: auto;
  max-width: none;
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

  .panel-result {
    max-width: none;
  }
}

@media (max-width: 768px) {
  .layout-fullscreen {
    flex-direction: column;
  }

  .layout-fullscreen .panel-result {
    height: 60vh;
  }
}
</style>
