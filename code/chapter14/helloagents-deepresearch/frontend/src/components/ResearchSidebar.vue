<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <button class="back-btn" @click="emit('back')" :disabled="loading">
        <svg viewBox="0 0 24 24" width="20" height="20">
          <path
            d="M19 12H5M12 19l-7-7 7-7"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
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
          <div
            class="progress-fill"
            :style="{ width: `${(completedTasks / totalTasks) * 100}%` }"
          ></div>
        </div>
        <p class="progress-text">{{ completedTasks }} / {{ totalTasks }} 个任务完成</p>
      </div>
    </div>

    <div class="sidebar-actions">
      <button class="new-research-btn" @click="emit('start-new')">
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path
            d="M12 5v14M5 12h14"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
            stroke-linecap="round"
          />
        </svg>
        开始新的求职分析
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { ResearchFormState } from "../types/research";

defineProps<{
  completedTasks: number;
  form: ResearchFormState;
  loading: boolean;
  totalTasks: number;
}>();

const emit = defineEmits<{
  back: [];
  "start-new": [];
}>();
</script>

<style scoped>
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
  font-size: 15px !important;
  font-weight: 600;
  color: #0f172a !important;
  padding: 12px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  border-left: 3px solid #3b82f6;
  white-space: pre-wrap;
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

@media (max-width: 1024px) {
  .sidebar {
    width: 320px;
    min-width: 320px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 100%;
    min-width: 100%;
    height: auto;
    max-height: 40vh;
  }
}
</style>
