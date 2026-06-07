<template>
  <div class="tasks-section" v-if="todoTasks.length">
    <aside class="tasks-list">
      <h3>任务清单</h3>
      <ul>
        <li
          v-for="task in todoTasks"
          :key="task.id"
          :class="[
            'task-item',
            { active: task.id === activeTaskId, completed: task.status === 'completed' }
          ]"
        >
          <button
            type="button"
            class="task-button"
            @click="emit('update:activeTaskId', task.id)"
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
              @click="emit('copy-note-path', currentTaskNotePath)"
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

      <section class="sources-block" :class="{ 'block-highlight': sourcesHighlight }">
        <div class="block-header">
          <h3>岗位/JD/渠道来源</h3>
          <button
            type="button"
            class="secondary-btn compact-btn"
            :disabled="!currentTaskSourcesText"
            @click="emit('copy-current-task-sources')"
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
        <p v-else class="muted">
          暂无岗位/JD/渠道来源，可以调整求职目标或切换搜索引擎后重试。
        </p>
      </section>

      <section class="summary-block" :class="{ 'block-highlight': summaryHighlight }">
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
                #{{ entry.eventId }} {{ entry.agent }} -> {{ entry.tool }}
              </span>
              <span v-if="entry.noteId" class="tool-entry-note">
                笔记：{{ entry.noteId }}
              </span>
            </div>
            <p v-if="entry.notePath" class="tool-entry-path">
              笔记路径：
              <button
                class="link-btn"
                type="button"
                @click="emit('copy-note-path', entry.notePath)"
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
</template>

<script setup lang="ts">
import type {
  SourceItem,
  TodoTaskView,
  ToolCallLog
} from "../types/research";
import {
  formatTaskStatus,
  formatToolParameters,
  formatToolResult
} from "../utils/researchFormatters";

defineProps<{
  activeTaskId: number | null;
  currentTask: TodoTaskView | null;
  currentTaskIntent: string;
  currentTaskNoteId: string;
  currentTaskNotePath: string;
  currentTaskQuery: string;
  currentTaskSources: SourceItem[];
  currentTaskSourcesText: string;
  currentTaskSummary: string;
  currentTaskTitle: string;
  currentTaskToolCalls: ToolCallLog[];
  sourcesHighlight: boolean;
  summaryHighlight: boolean;
  todoTasks: TodoTaskView[];
  toolHighlight: boolean;
}>();

const emit = defineEmits<{
  "copy-current-task-sources": [];
  "copy-note-path": [path: string | null | undefined];
  "update:activeTaskId": [value: number];
}>();
</script>

<style scoped>
.tasks-section {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
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

.sources-block h3,
.summary-block h3 {
  margin: 0 0 14px;
  color: #1f2937;
  letter-spacing: 0.02em;
}

.sources-block .block-header h3 {
  margin: 0;
}

.summary-block .block-pre,
.sources-block .block-pre {
  max-height: 360px;
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
  content: " ->";
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

@media (max-width: 960px) {
  .tasks-section {
    grid-template-columns: 1fr;
  }
}
</style>
