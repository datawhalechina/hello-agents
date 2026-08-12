<template>
  <div class="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
    <!-- Background decorations -->
    <div class="setup-bg-orb setup-bg-orb-1"></div>
    <div class="setup-bg-orb setup-bg-orb-2"></div>
    <div class="setup-bg-orb setup-bg-orb-3"></div>
    <div class="setup-bg-grid"></div>

    <div class="w-full max-w-xl relative z-10">
      <!-- Brand -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-[22px] bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 shadow-2xl shadow-blue-500/20 mb-6 ring-1 ring-white/10">
          <span class="text-4xl">🎙️</span>
        </div>
        <h1 class="text-5xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 tracking-tight">DeepCast</h1>
        <p class="text-base text-gray-400 font-light">进行深度研究并转化为引人入胜的播客</p>
      </div>

      <!-- Main Card -->
      <div class="setup-card rounded-2xl">
        <form @submit.prevent="$emit('start', topic)" class="p-7">
          <!-- Input area -->
          <div class="mb-5">
            <label for="topic-input" class="block text-sm font-medium text-gray-300 mb-2.5 flex items-center gap-2">
              <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
              播客主题
            </label>
            <textarea
              id="topic-input"
              v-model="topic"
              class="setup-textarea"
              placeholder="请输入播客主题（例如：AI Agent 的发展趋势）"
              required
              rows="4"
              aria-label="播客主题输入"
              @keydown.enter.prevent="$emit('start', topic)"
            ></textarea>
          </div>

          <!-- Feature badges -->
          <div class="flex flex-wrap gap-2 mb-6">
            <div class="setup-badge">
              <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              <span>混合搜索引擎</span>
            </div>
            <div class="setup-badge">
              <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
              <span>深度 AI 研究</span>
            </div>
            <div class="setup-badge">
              <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
              <span>自然语音合成</span>
            </div>
          </div>

          <!-- Submit button -->
          <button
            class="setup-btn w-full"
            :disabled="!topic.trim()"
            aria-label="开始制作播客"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            开始制作播客
          </button>
        </form>
      </div>

      <!-- Footer hint -->
      <p class="text-center text-xs text-gray-600 mt-5">基于 HelloAgents 框架 · 自动化深度研究 → 播客生成</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref } from "vue";

const topic = defineModel<string>("topic", { required: true });

defineEmits<{
  start: [topic: string];
}>();
</script>

<style scoped>
/* ── Background Decorations ── */
.setup-bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  opacity: 0.35;
}
.setup-bg-orb-1 {
  top: 10%;
  left: 15%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4), transparent 70%);
  animation: float-slow 8s ease-in-out infinite;
}
.setup-bg-orb-2 {
  bottom: 15%;
  right: 10%;
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.35), transparent 70%);
  animation: float-slow 10s ease-in-out infinite reverse;
}
.setup-bg-orb-3 {
  top: 50%;
  left: 60%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.25), transparent 70%);
  animation: float-slow 12s ease-in-out infinite 2s;
}
.setup-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

/* ── Main Card ── */
.setup-card {
  background: rgba(22, 24, 30, 0.8);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 25px 60px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* ── Textarea ── */
.setup-textarea {
  width: 100%;
  min-height: 110px;
  padding: 14px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  color: #e5e7eb;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.25s ease;
  outline: none;
  font-family: inherit;
}
.setup-textarea::placeholder {
  color: rgba(156, 163, 175, 0.5);
}
.setup-textarea:focus {
  background: rgba(0, 0, 0, 0.35);
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12), 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* ── Feature Badge ── */
.setup-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

/* ── Submit Button ── */
.setup-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow:
    0 4px 14px rgba(59, 130, 246, 0.3),
    inset 0 1px 1px rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: all 0.25s ease;
}
.setup-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow:
    0 8px 25px rgba(59, 130, 246, 0.35),
    inset 0 1px 1px rgba(255, 255, 255, 0.15);
  filter: brightness(1.05);
}
.setup-btn:active:not(:disabled) {
  transform: translateY(0.5px);
  filter: brightness(0.95);
}
.setup-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  filter: grayscale(0.4);
}

/* ── Animations ── */
@keyframes float-slow {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -15px); }
}
</style>
