<template>
  <div class="min-h-screen p-4 md:p-6">
    <div class="max-w-6xl mx-auto">
      <!-- Navbar -->
      <div class="player-nav rounded-2xl mb-6 px-6 py-3.5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span class="text-lg">🎙️</span>
            </div>
            <span class="text-xl font-bold text-white tracking-tight">DeepCast</span>
          </div>
          <div class="flex items-center gap-2">
            <button class="player-nav-btn text-blue-300" @click="$emit('downloadReport')" aria-label="下载研究报告">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              报告
            </button>
            <button class="player-nav-btn text-gray-400" @click="$emit('reset')" aria-label="制作新播客">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
              新播客
            </button>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-5 items-start">

        <!-- Left: Player Card -->
        <div class="lg:col-span-2">
          <div class="player-card rounded-2xl overflow-hidden">
            <!-- Album Art Area -->
            <div class="player-art-area">
              <div class="player-art-bg"></div>
              <div class="relative z-10 flex flex-col items-center py-10">
                <!-- Vinyl disc -->
                <div class="player-vinyl" :class="{ 'player-vinyl--spinning': isPlaying }">
                  <div class="player-vinyl-ring player-vinyl-ring-1"></div>
                  <div class="player-vinyl-ring player-vinyl-ring-2"></div>
                  <div class="player-vinyl-ring player-vinyl-ring-3"></div>
                  <div class="player-vinyl-groove"></div>
                  <!-- Center label -->
                  <div class="player-vinyl-label">
                    <span class="text-lg font-bold text-white tracking-tight">DC</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Info & Controls -->
            <div class="p-6">
              <div class="text-center mb-5">
                <h2 class="text-xl font-bold text-white leading-tight mb-1.5">{{ topic }}</h2>
                <p class="text-xs font-medium text-gray-500 tracking-[0.2em] uppercase">DeepCast Original</p>
              </div>

              <!-- Audio Player -->
              <div class="player-audio-wrap mb-5">
                <audio
                  ref="audioPlayer"
                  :src="audioUrl"
                  controls
                  class="w-full"
                  @play="isPlaying = true"
                  @pause="isPlaying = false"
                ></audio>
              </div>

              <!-- Action Buttons -->
              <div class="flex flex-col gap-2.5">
                <a :href="audioUrl" download class="player-btn-primary" aria-label="下载播客 MP3 文件">
                  <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                  下载 MP3
                </a>
                <button class="player-btn-ghost" @click="$emit('reset')" aria-label="制作新播客">
                  <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                  制作新播客
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Report -->
        <div class="lg:col-span-3">
          <div class="report-card rounded-2xl overflow-hidden" style="height: 75vh;">
            <!-- Report Header (macOS-style) -->
            <div class="report-header">
              <div class="flex items-center gap-2 mr-4">
                <div class="w-3 h-3 rounded-full bg-[#ff5f57]"></div>
                <div class="w-3 h-3 rounded-full bg-[#febc2e]"></div>
                <div class="w-3 h-3 rounded-full bg-[#28c840]"></div>
              </div>
              <div class="flex-1 text-center">
                <span class="text-sm font-medium text-gray-400 tracking-wide">研究报告</span>
              </div>
              <button class="report-download-btn" @click="$emit('downloadReport')" aria-label="下载研究报告">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              </button>
            </div>
            <!-- Report Content -->
            <div class="report-content custom-scrollbar" style="height: calc(100% - 48px);">
              <article class="prose prose-sm prose-invert max-w-none report-prose" v-html="renderedReport"></article>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from "vue";
import MarkdownIt from "markdown-it";

const md = new MarkdownIt();

const props = defineProps<{
  topic: string;
  audioUrl: string;
  reportMarkdown: string;
}>();

defineEmits<{
  reset: [];
  downloadReport: [];
}>();

const isPlaying = ref(false);
const audioPlayer = ref<HTMLAudioElement | null>(null);

const renderedReport = computed(() => md.render(props.reportMarkdown));
</script>

<style scoped>
/* ── Nav ── */
.player-nav {
  background: rgba(30, 32, 38, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.player-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: all 0.2s ease;
}
.player-nav-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
}

/* ── Player Card ── */
.player-card {
  background: rgba(22, 24, 30, 0.85);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 25px 60px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* ── Album Art Area ── */
.player-art-area {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 20, 50, 0.6));
}
.player-art-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 30% 50%, rgba(59, 130, 246, 0.15), transparent 60%),
    radial-gradient(ellipse at 70% 30%, rgba(139, 92, 246, 0.12), transparent 50%);
}

/* ── Vinyl Disc ── */
.player-vinyl {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, #1a1a2e 0%, #0d0d1a 100%);
  box-shadow:
    0 0 0 3px rgba(255, 255, 255, 0.05),
    0 10px 40px rgba(0, 0, 0, 0.5);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.5s ease;
}
.player-vinyl--spinning {
  animation: vinyl-spin 4s linear infinite;
}
.player-vinyl-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.04);
}
.player-vinyl-ring-1 { margin: 8px; }
.player-vinyl-ring-2 { margin: 22px; }
.player-vinyl-ring-3 { margin: 38px; }
.player-vinyl-groove {
  position: absolute;
  inset: 5px;
  border-radius: 50%;
  background: repeating-radial-gradient(
    circle at center,
    transparent 0px,
    transparent 3px,
    rgba(255, 255, 255, 0.02) 3px,
    rgba(255, 255, 255, 0.02) 4px
  );
}
.player-vinyl-label {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.2);
}

/* ── Audio Wrap ── */
.player-audio-wrap {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

/* ── Buttons ── */
.player-btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  color: white;
  text-decoration: none;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: all 0.2s ease;
}
.player-btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.15);
  filter: brightness(1.05);
}
.player-btn-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #9ca3af;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: all 0.2s ease;
}
.player-btn-ghost:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

/* ── Report Card ── */
.report-card {
  background: rgba(22, 24, 30, 0.85);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 25px 60px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.report-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(180deg, rgba(50, 52, 58, 0.9), rgba(38, 40, 46, 0.9));
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  user-select: none;
}
.report-download-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.report-download-btn:hover {
  color: #d1d5db;
  background: rgba(255, 255, 255, 0.06);
}
.report-content {
  overflow-y: auto;
  padding: 28px 32px;
  color: #d1d5db;
}
.report-prose :deep(h1) { color: #f3f4f6; font-size: 1.5em; margin-top: 1em; }
.report-prose :deep(h2) { color: #e5e7eb; font-size: 1.25em; margin-top: 0.8em; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.3em; }
.report-prose :deep(h3) { color: #d1d5db; font-size: 1.1em; }
.report-prose :deep(a) { color: #60a5fa; text-decoration: none; }
.report-prose :deep(a:hover) { text-decoration: underline; }
.report-prose :deep(code) { background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }
.report-prose :deep(blockquote) { border-left: 3px solid #3b82f6; padding-left: 1em; color: #9ca3af; }

/* ── Scrollbar ── */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }

/* ── Animation ── */
@keyframes vinyl-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
