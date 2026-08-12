<template>
  <div class="term-window rounded-2xl overflow-hidden" style="height: 500px;">
    <!-- macOS Title Bar -->
    <div class="term-titlebar">
      <!-- Traffic Lights -->
      <div class="flex items-center gap-[7px] mr-4">
        <div class="term-dot term-dot-red" title="关闭">
          <svg class="term-dot-icon" viewBox="0 0 12 12"><path d="M3.5 3.5l5 5M8.5 3.5l-5 5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
        </div>
        <div class="term-dot term-dot-yellow" title="最小化">
          <svg class="term-dot-icon" viewBox="0 0 12 12"><path d="M2.5 6h7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
        </div>
        <div class="term-dot term-dot-green" title="最大化">
          <svg class="term-dot-icon" viewBox="0 0 12 12"><path d="M3.5 8.5V5a1 1 0 011-1H8M8.5 3.5V7a1 1 0 01-1 1H4" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>
      <!-- Title -->
      <div class="flex-1 text-center">
        <div class="inline-flex items-center gap-2 px-3 py-0.5 rounded-md bg-white/[0.03]">
          <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <span class="text-[13px] font-medium text-gray-500 tracking-wide">deepcast — {{ logs.length }} lines</span>
        </div>
      </div>
      <!-- Placeholder for symmetry -->
      <div class="w-16"></div>
    </div>
    <!-- Terminal Content -->
    <div class="term-body custom-scrollbar" ref="logContainer" style="height: calc(100% - 48px);">
      <!-- Welcome Message -->
      <div v-if="logs.length === 0 && !isWaiting" class="term-welcome">
        <span class="term-prompt-user">deepcast</span><span class="text-gray-500">@</span><span class="term-prompt-host">studio</span>
        <span class="text-gray-500 mx-1">~</span>
        <span class="term-prompt-cmd">ready</span>
        <span class="term-cursor"></span>
      </div>
      <!-- Log Entries -->
      <div v-for="(log, i) in logs" :key="i" class="term-line" :class="getLogClass(log.message)">
        <span class="term-time">[{{ log.time }}]</span>
        <span class="term-text">{{ log.message }}</span>
      </div>
      <!-- Waiting States -->
      <div v-if="isWaiting && logs.length === 0" class="term-waiting-init">
        <div class="term-spinner"></div>
        <span>正在初始化...</span>
      </div>
      <div v-else-if="isWaiting" class="term-waiting">
        <span class="term-cursor"></span>
        <span>处理中{{ waitingDots }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, nextTick } from "vue";

export interface LogEntry {
  time: string;
  message: string;
}

defineProps<{
  logs: LogEntry[];
  isWaiting: boolean;
  waitingDots: string;
}>();

const logContainer = ref<HTMLElement | null>(null);

watch(
  () => logContainer.value,
  () => {},
  { flush: "post" }
);

defineExpose({ scrollToBottom });

function scrollToBottom() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
}

function getLogClass(message: string): string {
  if (message.includes("[STAGE]")) return "term-line--stage";
  if (message.includes("[TASK")) return "term-line--info";
  if (message.includes("[TOOL]")) return "term-line--tool";
  if (message.includes("[SOURCES]")) return "term-line--warning";
  if (message.includes("✅") || message.includes("status=completed")) return "term-line--success";
  if (message.includes("❌") || message.includes("ERROR") || message.includes("failed")) return "term-line--error";
  if (message.includes("⚠️") || message.includes("WARNING")) return "term-line--warning";
  if (message.includes("INFO:")) return "term-line--muted";
  if (message.includes("━")) return "term-line--divider";
  return "term-line--default";
}
</script>

<style scoped>
/* ── Terminal Window ── */
.term-window {
  background: #161618;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 25px 60px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

/* ── Title Bar ── */
.term-titlebar {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(180deg, rgba(50, 52, 58, 0.95), rgba(38, 40, 46, 0.95));
  border-bottom: 1px solid rgba(0, 0, 0, 0.4);
  user-select: none;
  -webkit-app-region: drag;
}

/* ── Traffic Light Dots ── */
.term-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: filter 0.15s;
}
.term-dot:hover { filter: brightness(1.15); }
.term-dot-icon {
  width: 8px;
  height: 8px;
  color: rgba(0, 0, 0, 0.5);
  opacity: 0;
  transition: opacity 0.15s;
}
.term-titlebar:hover .term-dot-icon { opacity: 1; }
.term-dot-red {
  background: #ff5f57;
  box-shadow: inset 0 -1px 1px rgba(0,0,0,0.15), 0 1px 2px rgba(255,95,87,0.2);
}
.term-dot-yellow {
  background: #febc2e;
  box-shadow: inset 0 -1px 1px rgba(0,0,0,0.15), 0 1px 2px rgba(254,188,46,0.2);
}
.term-dot-green {
  background: #28c840;
  box-shadow: inset 0 -1px 1px rgba(0,0,0,0.15), 0 1px 2px rgba(40,200,64,0.2);
}

/* ── Terminal Body ── */
.term-body {
  padding: 16px 18px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #d4d4d8;
  background:
    linear-gradient(180deg, rgba(22, 22, 24, 1) 0%, rgba(18, 18, 20, 1) 100%);
}

/* ── Welcome Prompt ── */
.term-welcome { margin-bottom: 4px; }
.term-prompt-user { color: #60a5fa; font-weight: 600; }
.term-prompt-host { color: #34d399; }
.term-prompt-cmd { color: #fbbf24; }

/* ── Cursor ── */
.term-cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  background: #60a5fa;
  margin-left: 4px;
  vertical-align: text-bottom;
  animation: cursor-blink 1s step-end infinite;
}

/* ── Log Lines ── */
.term-line {
  margin-bottom: 2px;
  padding: 1px 0;
  transition: background 0.15s;
}
.term-line:hover {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
}
.term-time {
  color: rgba(113, 113, 122, 0.7);
  font-size: 11px;
  margin-right: 10px;
  user-select: none;
  font-variant-numeric: tabular-nums;
}

/* ── Log Colors ── */
.term-line--stage { color: #60a5fa; font-weight: 600; }
.term-line--stage .term-time { color: rgba(96, 165, 250, 0.5); }
.term-line--info { color: #67e8f9; }
.term-line--tool { color: #c084fc; }
.term-line--success { color: #34d399; }
.term-line--error { color: #f87171; }
.term-line--warning { color: #fbbf24; }
.term-line--muted { color: #6b7280; }
.term-line--divider { color: rgba(63, 63, 70, 0.6); font-size: 12px; letter-spacing: -1px; }
.term-line--default { color: #d4d4d8; }

/* ── Waiting States ── */
.term-waiting-init {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fbbf24;
  padding-top: 32px;
}
.term-waiting {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fbbf24;
  margin-top: 6px;
}
.term-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(251, 191, 36, 0.3);
  border-top-color: #fbbf24;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* ── Scrollbar ── */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }
.term-body:not(:hover)::-webkit-scrollbar-thumb { background: transparent; }

/* ── Animations ── */
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
