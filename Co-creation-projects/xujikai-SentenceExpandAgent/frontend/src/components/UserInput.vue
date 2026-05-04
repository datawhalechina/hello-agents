<!--
用户输入框组件
用于手动模式下用户输入扩写的句子
-->
<template>
  <div class="user-input">
    <div class="input-header">
      <span class="user-avatar">✍️</span>
      <span class="user-name">你</span>
    </div>
    <div class="input-area">
      <textarea
        v-model="userSentence"
        class="sentence-textarea"
        placeholder="输入你的扩写句子..."
        rows="3"
        @keydown.enter.prevent="handleSubmit"
      />
      <button
        class="submit-btn"
        :disabled="!userSentence.trim() || loading"
        @click="handleSubmit"
      >
        {{ loading ? '提交中...' : '提交' }}
      </button>
    </div>
    <p v-if="error" class="error-message">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{
  submit: [sentence: string];
}>();

const userSentence = ref('');
const loading = ref(false);
const error = ref<string | null>(null);

async function handleSubmit() {
  if (!userSentence.value.trim()) {
    error.value = '请输入你的扩写句子';
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    emit('submit', userSentence.value.trim());
    userSentence.value = '';
  } catch (e) {
    error.value = e instanceof Error ? e.message : '提交失败，请重试';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.user-input {
  margin-bottom: 1.5rem;
}

.input-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.user-avatar {
  font-size: 1.5rem;
}

.user-name {
  font-weight: 600;
  color: #333;
}

.input-area {
  background: white;
  padding: 1rem;
  border-radius: 16px;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.sentence-textarea {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  resize: vertical;
  font-family: inherit;
  margin-bottom: 0.75rem;
  transition: border-color 0.3s;
}

.sentence-textarea:focus {
  outline: none;
  border-color: #4a90e2;
}

.submit-btn {
  width: 100%;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #4a90e2, #357abd);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.3);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  color: #e74c3c;
  margin-top: 0.5rem;
  font-size: 0.9rem;
}
</style>
