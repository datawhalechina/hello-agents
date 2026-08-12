<template>
  <div class="min-h-screen p-4 md:p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Navbar / Header -->
      <div class="nav-glass rounded-2xl shadow-lg mb-6 px-6 py-3.5">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span class="text-lg">🎙️</span>
            </div>
            <span class="text-xl font-bold text-white tracking-tight">DeepCast</span>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="reportReady" class="nav-action-btn text-blue-300" @click="$emit('downloadReport')" aria-label="下载研究报告">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              研究报告
            </button>
            <button v-if="!podcastReady" class="nav-action-btn text-red-400" @click="$emit('cancel')" aria-label="取消制作">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              取消
            </button>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-5">

        <!-- Left Column: Progress Steps -->
        <div class="lg:col-span-1">
          <div class="pipeline-card rounded-2xl h-[500px]">
            <!-- Top progress bar -->
            <div class="pipeline-progress-bar">
              <div class="pipeline-progress-fill" :style="{ width: progress + '%' }"></div>
            </div>

            <div class="p-5 h-full flex flex-col relative overflow-hidden">
              <!-- Ambient glow -->
              <div class="ambient-glow ambient-glow-1"></div>
              <div class="ambient-glow ambient-glow-2"></div>

              <!-- Header -->
              <div class="flex items-center gap-3 mb-2 z-10 relative">
                <div class="pipeline-icon-badge">
                  <span v-if="productionStage === 'done'" class="text-lg">✅</span>
                  <svg v-else class="w-5 h-5 text-blue-400 animate-spin-slow" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                </div>
                <div>
                  <h2 class="text-base font-bold text-white leading-tight">制作流程</h2>
                  <p class="text-[11px] text-gray-500 mt-0.5">{{ stageLabel }}</p>
                </div>
                <div class="ml-auto">
                  <span class="text-xs font-mono font-semibold text-blue-400/80">{{ progress }}%</span>
                </div>
              </div>

              <!-- Divider -->
              <div class="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-3"></div>

              <!-- Timeline Steps -->
              <div class="flex-1 flex flex-col justify-center gap-1 z-10 relative">
                <div v-for="(step, idx) in pipelineSteps" :key="step.id"
                  class="pipeline-step group"
                  :class="{
                    'pipeline-step--completed': isStepCompleted(step.id),
                    'pipeline-step--active': isStepActive(step.id),
                    'pipeline-step--pending': isStepPending(step.id),
                  }">
                  <!-- Connector line -->
                  <div v-if="idx < pipelineSteps.length - 1" class="pipeline-connector"
                    :class="{
                      'pipeline-connector--completed': isStepCompleted(step.id),
                      'pipeline-connector--active': isStepActive(step.id),
                    }"></div>

                  <!-- Step indicator -->
                  <div class="pipeline-indicator">
                    <!-- Completed -->
                    <svg v-if="isStepCompleted(step.id)" class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                    <!-- Active pulse -->
                    <div v-else-if="isStepActive(step.id)" class="pipeline-pulse"></div>
                    <!-- Pending dot -->
                    <div v-else class="w-2 h-2 rounded-full bg-gray-600"></div>
                  </div>

                  <!-- Step content -->
                  <div class="pipeline-step-content">
                    <div class="flex items-center gap-2">
                      <span class="text-base" :class="{ 'animate-float': isStepActive(step.id) }">{{ step.icon }}</span>
                      <span class="step-label text-sm font-semibold" :class="isStepActive(step.id) ? 'text-white' : isStepCompleted(step.id) ? 'text-gray-300' : 'text-gray-500'">{{ step.label }}</span>
                    </div>
                    <p class="step-desc text-[11px] mt-0.5 ml-7" :class="isStepActive(step.id) ? 'text-gray-400' : 'text-gray-600'">{{ step.desc }}</p>
                  </div>
                </div>
              </div>

              <!-- Bottom status chip -->
              <div class="z-10 relative mt-3">
                <div class="pipeline-status-chip" :class="{
                  'pipeline-status-chip--done': productionStage === 'done',
                  'pipeline-status-chip--cancelled': isCancelled
                }">
                  <span class="inline-block w-1.5 h-1.5 rounded-full mr-2" :class="
                    productionStage === 'done' ? 'bg-emerald-400' :
                    isCancelled ? 'bg-red-400' :
                    'bg-blue-400 animate-pulse'
                  "></span>
                  <span class="text-[11px] font-medium">{{
                    productionStage === 'done' ? '制作完成' :
                    isCancelled ? '已取消' :
                    '正在处理...'
                  }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Logs & Output -->
        <div class="lg:col-span-3 flex flex-col gap-4">

          <!-- macOS Style Terminal -->
          <TerminalLog ref="terminalRef" :logs="logs" :is-waiting="isWaiting" :waiting-dots="waitingDots" />

          <!-- Result Actions -->
          <div v-if="podcastReady" class="flex gap-3">
            <a :href="audioUrl" download class="btn macos-btn-primary flex-1 btn-lg text-base rounded-xl border-0 gap-2">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              下载 MP3
            </a>
            <button class="btn result-btn-secondary flex-1 btn-lg text-base rounded-xl gap-2" @click="$emit('goPlayer')">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
              进入播放器
            </button>
          </div>

          <!-- Inline Player -->
          <div v-if="podcastReady" class="player-inline-card rounded-xl">
            <div class="p-4">
              <div class="flex items-center gap-2.5 mb-3">
                <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md">
                  <svg class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 20 20"><path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z"/></svg>
                </div>
                <h3 class="text-sm font-semibold text-gray-200">快速试听</h3>
              </div>
              <audio class="w-full audio-player" :src="audioUrl" controls></audio>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, toRef } from "vue";
import TerminalLog from "./TerminalLog.vue";
import type { LogEntry } from "./TerminalLog.vue";

export type ProductionStage = "research" | "script" | "audio" | "done" | "cancelled";

interface PipelineStep {
  id: ProductionStage;
  icon: string;
  label: string;
  desc: string;
}

const pipelineSteps: PipelineStep[] = [
  { id: "research", icon: "🔍", label: "深度研究", desc: "网络搜索 & 信息聚合" },
  { id: "script", icon: "✍️", label: "剧本创作", desc: "生成对话 & 角色分配" },
  { id: "audio", icon: "🎵", label: "音频合成", desc: "TTS 语音生成 & 拼接" },
  { id: "done", icon: "🎉", label: "制作完成", desc: "播放 & 下载播客" },
];

const stepsOrder: ProductionStage[] = ["research", "script", "audio", "done"];

const props = defineProps<{
  logs: LogEntry[];
  isWaiting: boolean;
  waitingDots: string;
  productionStage: ProductionStage;
  progressPercent: number;
  reportReady: boolean;
  podcastReady: boolean;
  audioUrl: string;
}>();

defineEmits<{
  cancel: [];
  downloadReport: [];
  goPlayer: [];
}>();

const terminalRef = ref<InstanceType<typeof TerminalLog> | null>(null);

function scrollTerminal() {
  terminalRef.value?.scrollToBottom();
}

defineExpose({ scrollTerminal });

const progress = toRef(props, 'progressPercent');
const currentIdx = computed(() => stepsOrder.indexOf(props.productionStage));

const isCancelled = computed(() => props.productionStage === 'cancelled');

const stageLabel = computed(() => {
  const labels: Record<ProductionStage, string> = {
    research: "正在进行深度研究...",
    script: "正在创作剧本...",
    audio: "正在合成音频...",
    done: "播客制作完成！",
    cancelled: "已取消制作",
  };
  return labels[props.productionStage] || "";
});

function isStepCompleted(stepId: ProductionStage) {
  return currentIdx.value > stepsOrder.indexOf(stepId);
}

function isStepActive(stepId: ProductionStage) {
  return currentIdx.value === stepsOrder.indexOf(stepId);
}

function isStepPending(stepId: ProductionStage) {
  return currentIdx.value < stepsOrder.indexOf(stepId);
}
</script>

<style scoped>
/* ── Pipeline Card ── */
.pipeline-card {
  background: rgba(22, 24, 30, 0.85);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

/* ── Top Progress Bar ── */
.pipeline-progress-bar {
  height: 3px;
  background: rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}
.pipeline-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4);
  background-size: 200% 100%;
  animation: shimmer 2s ease-in-out infinite;
  transition: width 1.2s cubic-bezier(0.22, 1, 0.36, 1);
  border-radius: 0 2px 2px 0;
}

/* ── Ambient Glow ── */
.ambient-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  opacity: 0.4;
}
.ambient-glow-1 {
  top: -30px;
  right: -30px;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.3), transparent 70%);
}
.ambient-glow-2 {
  bottom: -20px;
  left: -20px;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.25), transparent 70%);
}

/* ── Header Icon Badge ── */
.pipeline-icon-badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* ── Pipeline Step ── */
.pipeline-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 8px;
  border-radius: 10px;
  position: relative;
  border: 1px solid transparent;
  margin: 0;
  transition:
    background 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    padding 0.5s cubic-bezier(0.4, 0, 0.2, 1),
    margin 0.5s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.pipeline-step--active {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.15);
  margin: 0 -4px;
  padding: 10px 12px;
  transform: scale(1.02);
}
.pipeline-step--completed {
  opacity: 0.85;
}

/* ── Connector Line ── */
.pipeline-connector {
  position: absolute;
  left: 21px;
  top: 38px;
  width: 2px;
  height: calc(100% - 10px);
  border-radius: 1px;
  z-index: 1;
  overflow: hidden;
}
/* Use a pseudo-element to animate the fill from top to bottom */
.pipeline-connector::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.06);
  transition: opacity 0.6s ease;
}
.pipeline-connector::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 0%;
  background: linear-gradient(180deg, #3b82f6, #8b5cf6);
  border-radius: 1px;
  transition: height 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.pipeline-connector--completed::after {
  height: 100%;
}
.pipeline-connector--active::after {
  height: 60%;
  background: linear-gradient(180deg, #3b82f6 0%, rgba(59, 130, 246, 0.15) 100%);
}

/* ── Step Indicator ── */
.pipeline-indicator {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
  margin-top: 1px;
  background: rgba(255, 255, 255, 0.04);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
  transition:
    background 0.5s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.5s cubic-bezier(0.4, 0, 0.2, 1),
    border-width 0.3s ease,
    box-shadow 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.pipeline-step--completed .pipeline-indicator {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
  transform: scale(1);
  animation: indicator-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.pipeline-step--active .pipeline-indicator {
  background: rgba(59, 130, 246, 0.15);
  border: 2px solid #3b82f6;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
  animation: indicator-glow-in 0.6s ease;
}
.pipeline-step--pending .pipeline-indicator {
  background: rgba(255, 255, 255, 0.04);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
}

/* ── Active Pulse Dot ── */
.pipeline-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse-ring 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  box-shadow: 0 0 6px rgba(59, 130, 246, 0.6);
}

/* ── Step Content ── */
.pipeline-step-content {
  flex: 1;
  min-width: 0;
}
.step-label, .step-desc {
  transition: color 0.5s ease;
}

/* ── Status Chip ── */
.pipeline-status-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.12);
  color: #93c5fd;
  transition:
    background 0.5s ease,
    border-color 0.5s ease,
    color 0.5s ease;
}
.pipeline-status-chip--done {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
}
.pipeline-status-chip--cancelled {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

/* ── Navbar ── */
.nav-glass {
  background: rgba(30, 32, 38, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.nav-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: all 0.2s ease;
  cursor: pointer;
}
.nav-action-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
}

/* ── Result Buttons ── */
.macos-btn-primary {
  background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.15);
  transition: all 0.2s;
}
.macos-btn-primary:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.15);
}
.macos-btn-primary:active { transform: translateY(0.5px); filter: brightness(0.95); }

.result-btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}
.result-btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

/* ── Inline Player ── */
.player-inline-card {
  background: rgba(22, 24, 30, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}
.audio-player {
  opacity: 0.9;
  border-radius: 8px;
  transition: opacity 0.2s;
}
.audio-player:hover {
  opacity: 1;
}

/* ── Animations ── */
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin-slow { animation: spin-slow 2s linear infinite; }

@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}
.animate-float { animation: float 2s ease-in-out infinite; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes indicator-pop {
  0% { transform: scale(0.6); opacity: 0.5; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes indicator-glow-in {
  0% { box-shadow: 0 0 0 rgba(59, 130, 246, 0); }
  50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); }
  100% { box-shadow: 0 0 12px rgba(59, 130, 246, 0.25); }
}
</style>
