<!--
最终结果组件
显示润色后的满分版本
-->
<template>
  <div class="final-result">
    <div class="result-header">
      <span class="icon">🏆</span>
      <h2 class="title">满分版本</h2>
    </div>

    <div class="result-content">
      <p class="seed-label">原始句子：</p>
      <p class="seed-text">{{ seedSentence }}</p>

      <div class="divider"></div>

      <p class="final-label">润色后：</p>
      <p class="final-text">{{ polishedSentence }}</p>
    </div>

    <button class="restart-btn" @click="handleRestart">
      🔄 开始新的扩写
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  seedSentence: string;
  polishedSentence: string;
}>();

const emit = defineEmits<{
  restart: [];
}>();

function handleRestart() {
  emit('restart');
}
</script>

<style scoped>
.final-result {
  max-width: 700px;
  margin: 2rem auto;
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.icon {
  font-size: 2rem;
}

.title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  background: linear-gradient(135deg, #ffc107, #ff9800);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.result-content {
  background: linear-gradient(135deg, #fff9e6, #fff3cd);
  padding: 2rem;
  border-radius: 16px;
  border: 3px solid #ffc107;
  box-shadow: 0 4px 16px rgba(255, 193, 7, 0.3);
  margin-bottom: 1.5rem;
}

.seed-label,
.final-label {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.seed-text {
  margin: 0 0 1rem 0;
  color: #333;
  line-height: 1.6;
  font-size: 1rem;
  font-style: italic;
}

.divider {
  height: 2px;
  background: linear-gradient(90deg, transparent, #ffc107, transparent);
  margin: 1.5rem 0;
}

.final-text {
  margin: 0;
  color: #333;
  line-height: 1.8;
  font-size: 1.15rem;
  font-weight: 500;
}

.restart-btn {
  display: block;
  width: 100%;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #28a745, #218843);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.restart-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
}
</style>
