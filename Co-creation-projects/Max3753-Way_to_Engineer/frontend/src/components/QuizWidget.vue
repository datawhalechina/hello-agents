<template>
  <div class="quiz-widget" :class="{ answered, correct: isCorrect, wrong: !isCorrect && answered }">
    <div class="quiz-header">
      <span class="quiz-badge">📝 测验</span>
      <span v-if="answered" class="quiz-result" :class="isCorrect ? 'correct' : 'wrong'">
        {{ isCorrect ? '✓ 正确！' : '✗ 错误' }}
      </span>
    </div>

    <div v-if="data.code" class="quiz-code-block">
      <pre><code>{{ data.code }}</code></pre>
    </div>
    <p class="quiz-question">{{ data.question }}</p>

    <div class="quiz-options">
      <div
        v-for="(option, index) in data.options"
        :key="index"
        :class="[
          'quiz-option',
          {
            selected: selectedIndex === index,
            correct: answered && index === data.correct,
            wrong: answered && selectedIndex === index && index !== data.correct,
            disabled: answered,
          }
        ]"
        @click="selectOption(index)"
      >
        <span class="option-radio">
          <span v-if="answered && index === data.correct" class="check">✓</span>
          <span v-else-if="answered && selectedIndex === index && index !== data.correct" class="cross">✗</span>
          <span v-else class="dot"></span>
        </span>
        <span class="option-text">{{ option.replace(/^[A-D]\.\s*/, '') }}</span>
      </div>
    </div>

    <Transition name="explain-fade">
      <div v-if="answered" class="quiz-explanation">
        <div class="explain-icon">{{ isCorrect ? '🎉' : '💡' }}</div>
        <div class="explain-text">{{ data.explanation }}</div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface QuizData {
  question: string
  options: string[]
  correct: number
  explanation: string
  code?: string
}

const props = defineProps<{
  data: QuizData
}>()

const emit = defineEmits<{
  answer: [correct: boolean]
}>()

const selectedIndex = ref<number | null>(null)
const answered = ref(false)

const isCorrect = ref(false)

const selectOption = (index: number) => {
  if (answered.value) return
  selectedIndex.value = index
  answered.value = true
  // coerce correct to number (AI sometimes outputs string)
  const correctIndex = typeof props.data.correct === 'number' ? props.data.correct : Number(props.data.correct)
  isCorrect.value = index === correctIndex
  emit('answer', isCorrect.value)
}
</script>

<style scoped>
.quiz-widget {
  margin: 12px 0;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border: 1px solid #e0e4f0;
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
}

.quiz-widget.answered {
  background: #fff;
}

.quiz-widget.correct {
  border-color: #b7eb8f;
  box-shadow: 0 0 0 1px rgba(82, 196, 26, 0.1);
}

.quiz-widget.wrong {
  border-color: #ffccc7;
  box-shadow: 0 0 0 1px rgba(255, 77, 79, 0.1);
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.quiz-badge {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  padding: 2px 10px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 10px;
}

.quiz-result {
  font-size: 13px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 10px;
}

.quiz-result.correct {
  color: #52c41a;
  background: rgba(82, 196, 26, 0.1);
}

.quiz-result.wrong {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

.quiz-code-block {
  margin: 0 0 12px 0;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.quiz-code-block pre {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
}

.quiz-code-block code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #d4d4d4;
  white-space: pre;
}

.quiz-question {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
  line-height: 1.6;
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quiz-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: white;
  border: 1.5px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #333;
}

.quiz-option:hover:not(.disabled) {
  border-color: #667eea;
  background: #f8f9ff;
}

.quiz-option.selected:not(.answered) {
  border-color: #667eea;
  background: #f0f2ff;
}

.quiz-option.correct {
  border-color: #52c41a;
  background: #f6ffed;
  color: #135200;
}

.quiz-option.wrong {
  border-color: #ff4d4f;
  background: #fff2f0;
  color: #820014;
}

.quiz-option.disabled {
  cursor: default;
  opacity: 0.85;
}

.option-radio {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid #d9d9d9;
  transition: all 0.2s;
}

.quiz-option.selected .option-radio {
  border-color: #667eea;
  background: #667eea;
}

.quiz-option.correct .option-radio {
  border-color: #52c41a;
  background: #52c41a;
}

.quiz-option.wrong .option-radio {
  border-color: #ff4d4f;
  background: #ff4d4f;
}

.option-radio .dot {
  width: 8px;
  height: 8px;
  background: transparent;
  border-radius: 50%;
}

.quiz-option.selected .option-radio .dot {
  background: white;
}

.option-radio .check,
.option-radio .cross {
  color: white;
  font-size: 11px;
  font-weight: bold;
}

.option-text {
  flex: 1;
  line-height: 1.4;
}

.quiz-explanation {
  margin-top: 12px;
  padding: 12px 14px;
  background: #f8f9fa;
  border-radius: 10px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.explain-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.explain-text {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

/* Transition */
.explain-fade-enter-active {
  transition: all 0.3s ease;
}

.explain-fade-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
