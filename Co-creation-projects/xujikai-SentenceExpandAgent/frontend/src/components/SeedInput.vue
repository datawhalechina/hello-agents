<!--
种子句输入组件
用户输入英文种子句并选择模式
-->
<template>
  <div class="seed-input">
    <h2 class="title">英语句子扩写智能体</h2>
    <p class="subtitle">通过记者提问法将简单句子逐步扩写为高级长句</p>

    <div class="input-group">
      <textarea
        v-model="inputSentence"
        class="sentence-input"
        placeholder="输入一个简单的英文句子，例如：I like reading."
        rows="3"
        @keydown.enter.prevent="handleSubmit"
      />
    </div>

    <div class="mode-selector">
      <button
        class="mode-btn"
        :class="{ active: selectedMode === 'manual' }"
        @click="selectedMode = 'manual'"
      >
        📝 手动模式
        <span class="mode-desc">逐步引导，逐阶段回答</span>
      </button>
      <button
        class="mode-btn"
        :class="{ active: selectedMode === 'auto' }"
        @click="selectedMode = 'auto'"
      >
        🚀 自动模式
        <span class="mode-desc">一键自动演示全过程</span>
      </button>
    </div>

    <button
      class="submit-btn"
      :disabled="!inputSentence.trim() || loading"
      @click="handleSubmit"
    >
      {{ loading ? '正在启动...' : '开始扩写' }}
    </button>

    <p v-if="error" class="error-message">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useSessionStore } from '../stores/session';
import type { Mode } from '../types/expand';

const emit = defineEmits<{
  start: [sentence: string, mode: Mode];
}>();

const sessionStore = useSessionStore();

const inputSentence = ref('');
const selectedMode = ref<Mode>('manual');
const loading = ref(false);
const error = ref<string | null>(null);

function handleSubmit() {
  if (!inputSentence.value.trim()) {
    error.value = '请输入一个英文句子';
    return;
  }

  // 通过 emit 事件将数据传递给父组件，由父组件调用 sessionStore
  emit('start', inputSentence.value.trim(), selectedMode.value);
}
</script>

<style scoped>
.seed-input {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1rem;
  color: #666;
  margin-bottom: 2rem;
}

.input-group {
  margin-bottom: 1.5rem;
}

.sentence-input {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.3s;
}

.sentence-input:focus {
  outline: none;
  border-color: #4a90e2;
}

.mode-selector {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  justify-content: center;
}

.mode-btn {
  flex: 1;
  padding: 1rem 1.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.mode-btn:hover {
  border-color: #4a90e2;
  background: #f8f9fa;
}

.mode-btn.active {
  border-color: #4a90e2;
  background: #e8f4ff;
  font-weight: 600;
}

.mode-desc {
  font-size: 0.85rem;
  color: #666;
  font-weight: normal;
}

.submit-btn {
  width: 100%;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #4a90e2, #357abd);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  color: #e74c3c;
  margin-top: 1rem;
  font-size: 0.9rem;
}
</style>
