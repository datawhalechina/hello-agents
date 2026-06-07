<template>
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
        任务进度：{{ completedTasks }} / {{ totalTasks || todoTasksLength || 1 }}
        · 阶段记录 {{ progressLogs.length }} 条
      </span>
    </div>
    <div class="status-controls">
      <button
        v-if="canRetryStream"
        type="button"
        class="secondary-btn"
        @click="emit('retry')"
      >
        重新尝试
      </button>
      <button class="secondary-btn" @click="emit('toggle-logs')">
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
</template>

<script setup lang="ts">
import type { StreamStatus } from "../types/research";

defineProps<{
  canRetryStream: boolean;
  completedTasks: number;
  loading: boolean;
  logsCollapsed: boolean;
  progressLogs: string[];
  streamStatus: StreamStatus;
  streamStatusLabel: string;
  todoTasksLength: number;
  totalTasks: number;
}>();

const emit = defineEmits<{
  retry: [];
  "toggle-logs": [];
}>();
</script>

<style scoped>
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

@media (max-width: 960px) {
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
  .status-meta {
    font-size: 12px;
  }
}
</style>
