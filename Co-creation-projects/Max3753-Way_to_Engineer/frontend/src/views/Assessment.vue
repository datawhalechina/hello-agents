<template>
  <div class="assessment-view">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ langStore.t('assessment.loading') }}</p>
    </div>

    <!-- 测试进行中 -->
    <div v-else-if="currentQuestion && !completed" class="assessment-content">
      <div class="assessment-header">
        <div class="header-left">
          <h1>{{ langStore.t('assessment.title') }}</h1>
          <p class="path-label">{{ getPathTitle(pathType) }}</p>
        </div>
        <div class="header-right">
          <div class="progress-info">
            <span class="question-count">{{ langStore.t('assessment.questionProgress', { current: currentIndex + 1, total: totalQuestions }) }}</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="question-card">
        <div class="question-meta">
          <span class="category-badge">{{ getCategoryName(currentQuestion.category) }}</span>
          <span class="difficulty-badge" :class="getDifficultyClass(currentQuestion.difficulty)">
            {{ getDifficultyText(currentQuestion.difficulty) }}
          </span>
          <span class="type-badge" :class="currentQuestion.question_type">
            {{ getQuestionTypeText(currentQuestion.question_type) }}
          </span>
        </div>

        <h2 class="question-content">{{ currentQuestion.content }}</h2>

        <!-- 代码片段 -->
        <div v-if="currentQuestion.code_snippet" class="code-block">
          <pre><code>{{ currentQuestion.code_snippet }}</code></pre>
        </div>

        <div class="options-list">
          <div
            v-for="(option, index) in currentQuestion.options"
            :key="index"
            :class="[
              'option-item',
              {
                selected: selectedAnswer === getOptionLetter(index),
                correct: showResult && getOptionLetter(index) === currentQuestion.correct_answer,
                wrong: showResult && selectedAnswer === getOptionLetter(index) && getOptionLetter(index) !== currentQuestion.correct_answer
              }
            ]"
            @click="selectAnswer(getOptionLetter(index))"
          >
            <span class="option-letter">{{ getOptionLetter(index) }}</span>
            <span class="option-text">{{ getOptionText(option) }}</span>
            <span v-if="showResult && getOptionLetter(index) === currentQuestion.correct_answer" class="result-icon correct">✓</span>
            <span v-else-if="showResult && selectedAnswer === getOptionLetter(index)" class="result-icon wrong">✗</span>
          </div>
        </div>

        <!-- 答案解析 -->
        <div v-if="showResult" class="explanation-box">
          <div class="explanation-header">
            <span class="explanation-icon">{{ lastAnswerCorrect ? '🎉' : '💡' }}</span>
            <span class="explanation-title">{{ lastAnswerCorrect ? langStore.t('assessment.answerCorrect') : langStore.t('assessment.answerWrong') }}</span>
          </div>
          <p class="explanation-text">{{ currentQuestion.explanation }}</p>
        </div>

        <div class="action-buttons">
          <button
            v-if="!showResult"
            class="btn btn-primary"
            :disabled="!selectedAnswer"
            @click="submitAnswer"
          >
            {{ langStore.t('assessment.confirmAnswer') }}
          </button>
          <button
            v-else
            class="btn btn-primary"
            @click="nextQuestion"
          >
            {{ currentIndex >= totalQuestions - 1 ? langStore.t('assessment.viewResult') : langStore.t('assessment.nextQuestion') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 测试结果 -->
    <div v-else-if="completed && assessmentResult" class="result-content">
      <div class="result-card">
        <div class="result-header">
          <div class="score-circle" :class="getScoreClass(assessmentResult.score)">
            <span class="score-value">{{ assessmentResult.score }}</span>
            <span class="score-label">{{ langStore.t('assessment.unit') }}</span>
          </div>
          <div class="result-summary">
            <h1>{{ langStore.t('assessment.testComplete') }}</h1>
            <p class="level-text">
              {{ langStore.t('assessment.yourLevel') }}<span :class="['level-badge', assessmentResult.level]">{{ getLevelText(assessmentResult.level) }}</span>
            </p>
            <p class="correct-text">{{ langStore.t('assessment.correctCount', { correct: assessmentResult.correct_count, total: assessmentResult.total_questions }) }}</p>
          </div>
        </div>

        <!-- 分类得分 -->
        <div class="category-scores">
          <h3>{{ langStore.t('assessment.categoryScores') }}</h3>
          <div class="scores-grid">
            <div
              v-for="(score, category) in assessmentResult.category_scores"
              :key="category"
              class="score-item"
            >
              <div class="score-header">
                <span class="category-name">{{ getCategoryName(category) }}</span>
                <span class="category-score">{{ score }}%</span>
              </div>
              <div class="score-bar">
                <div class="score-fill" :style="{ width: score + '%' }" :class="getScoreBarClass(score)"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 推荐 -->
        <div class="recommendation-box">
          <div class="rec-icon">🎯</div>
          <div class="rec-content">
            <h3>{{ langStore.t('assessment.learningSuggestion') }}</h3>
            <p>{{ langStore.t('assessment.suggestionDesc', { module: getModuleName(assessmentResult.recommended_start_module) }) }}</p>
          </div>
        </div>

        <div class="result-actions">
          <button class="btn btn-primary" @click="startLearning">
            {{ langStore.t('assessment.startLearning') }}
          </button>
          <button class="btn btn-outline" @click="retakeTest">
            {{ langStore.t('assessment.retake') }}
          </button>
          <button class="btn btn-outline" @click="goBack">
            {{ langStore.t('assessment.goBack') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { useLangStore } from '../stores/langStore'
import { getLevelText, getCategoryName, getScoreBarClass, getModuleName, getQuestionTypeText, getDifficultyText, getDifficultyClass } from '../utils/helpers'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const langStore = useLangStore()

// 状态
const loading = ref(true)
const pathType = ref('')
const sessionId = ref('')
const currentQuestion = ref<any>(null)
const currentIndex = ref(0)
const totalQuestions = ref(10)
const selectedAnswer = ref('')
const showResult = ref(false)
const lastAnswerCorrect = ref(false)
const completed = ref(false)
const assessmentResult = ref<any>(null)
const nextQuestionData = ref<any>(null)

// 计算属性
const progressPercent = computed(() => {
  return (currentIndex.value / totalQuestions.value) * 100
})

// 初始化
onMounted(async () => {
  // 从query获取pathType
  pathType.value = (route.query.path as string) || 'frontend'

  // 开始测试
  await startTest()
})

// 开始测试
const startTest = async () => {
  loading.value = true
  try {
    const response = await axios.post('/api/assessment/start', {
      path_type: pathType.value,
      user_id: authStore.userId,
    })
    sessionId.value = response.data.session_id
    currentQuestion.value = response.data.question
    totalQuestions.value = response.data.total_questions
    currentIndex.value = response.data.current_index
    loading.value = false
  } catch (error) {
    console.error('Failed to start assessment:', error)
    loading.value = false
    alert('启动测试失败，请重试')
  }
}

// 选择答案
const selectAnswer = (letter: string) => {
  if (!showResult.value) {
    selectedAnswer.value = letter
  }
}

// 提交答案
const submitAnswer = async () => {
  if (!selectedAnswer.value) return

  try {
    const response = await axios.post('/api/assessment/answer', {
      session_id: sessionId.value,
      question_id: currentQuestion.value.id,
      answer: selectedAnswer.value,
      path_type: pathType.value,
      user_id: authStore.userId,
    })

    lastAnswerCorrect.value = response.data.is_correct
    showResult.value = true

    // 保存下一题信息（不立即切换，等用户点击"下一题"）
    if (response.data.is_completed) {
      // 测试完成
      assessmentResult.value = response.data.assessment_result
      completed.value = true
    } else {
      // 暂存下一题
      nextQuestionData.value = response.data.next_question
    }
  } catch (error) {
    console.error('Failed to submit answer:', error)
  }
}

// 下一题
const nextQuestion = () => {
  // 切换到下一题
  if (nextQuestionData.value) {
    currentQuestion.value = nextQuestionData.value
    currentIndex.value++
    nextQuestionData.value = null
  }
  showResult.value = false
  selectedAnswer.value = ''
  lastAnswerCorrect.value = false
}

// 开始学习
const startLearning = () => {
  // 存储学习上下文到sessionStorage
  const context = {
    message: `我已经完成了水平检测，得分${assessmentResult.value.score}分，水平为${getLevelText(assessmentResult.value.level)}。请根据我的测试结果，从"${getModuleName(assessmentResult.value.recommended_start_module)}"模块开始帮我制定学习计划。`,
    path_type: pathType.value,
    user_level: assessmentResult.value.level,
    skill_levels: assessmentResult.value.category_scores,
    recommended_module: assessmentResult.value.recommended_start_module,
    is_assessment_result: true
  }
  sessionStorage.setItem('pendingLearningContext', JSON.stringify(context))

  // 跳转到聊天页面
  router.push('/')
}

// 重新测试
const retakeTest = async () => {
  loading.value = true
  completed.value = false
  assessmentResult.value = null
  selectedAnswer.value = ''
  showResult.value = false
  await startTest()
}

// 返回
const goBack = () => {
  router.push('/learning')
}

// 工具函数
const getOptionLetter = (index: number) => {
  return String.fromCharCode(65 + index) // A, B, C, D
}

const getOptionText = (option: string) => {
  // 移除开头的"A. ", "B. "等
  return option.replace(/^[A-D]\.\s*/, '')
}

const getPathTitle = (path: string) => {
  const titles: Record<string, string> = {
    frontend: '前端开发',
    backend: '后端开发',
    fullstack: '全栈开发'
  }
  return titles[path] || path
}

const getScoreClass = (score: number) => {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'fair'
  return 'poor'
}
</script>

<style scoped>
.assessment-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: #f8f9fa;
  overflow-y: auto;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e8e8e8;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: #666;
  font-size: 16px;
}

/* 测试头部 */
.assessment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  background: white;
  border-bottom: 1px solid #e5e5e5;
}

.header-left h1 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #1a1a1a;
}

.path-label {
  margin: 0;
  color: #667eea;
  font-size: 14px;
  font-weight: 500;
}

.progress-info {
  text-align: right;
}

.question-count {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s;
}

/* 题目卡片 */
.assessment-content {
  padding: 32px;
}

.question-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.question-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.category-badge {
  padding: 4px 12px;
  background: #e6f7ff;
  color: #1890ff;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.difficulty-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.difficulty-badge.easy { background: #f6ffed; color: #52c41a; }
.difficulty-badge.medium { background: #fff7e6; color: #fa8c16; }
.difficulty-badge.hard { background: #fff2f0; color: #ff4d4f; }

.type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}
.type-badge.choice { background: #f0f5ff; color: #2f54eb; }
.type-badge.code_output { background: #f9f0ff; color: #722ed1; }
.type-badge.code_fill { background: #e6fffb; color: #13c2c2; }
.type-badge.bug_fix { background: #fff1f0; color: #cf1322; }

.question-content {
  margin: 0 0 28px 0;
  font-size: 18px;
  color: #1a1a1a;
  line-height: 1.6;
}

/* 代码块 */
.code-block {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
  overflow-x: auto;
}

.code-block pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #d4d4d4;
}

.code-block code {
  white-space: pre;
}

/* 选项 */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-item:hover:not(.correct):not(.wrong) {
  background: #e8e8e8;
  border-color: #d9d9d9;
}

.option-item.selected {
  background: #e6f7ff;
  border-color: #667eea;
}

.option-item.correct {
  background: #f6ffed;
  border-color: #52c41a;
}

.option-item.wrong {
  background: #fff2f0;
  border-color: #ff4d4f;
}

.option-letter {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 50%;
  font-weight: 600;
  font-size: 14px;
  color: #666;
  border: 1px solid #d9d9d9;
  flex-shrink: 0;
}

.option-item.selected .option-letter {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.option-item.correct .option-letter {
  background: #52c41a;
  color: white;
  border-color: #52c41a;
}

.option-item.wrong .option-letter {
  background: #ff4d4f;
  color: white;
  border-color: #ff4d4f;
}

.option-text {
  flex: 1;
  font-size: 15px;
  color: #333;
  line-height: 1.5;
}

.result-icon {
  font-size: 18px;
  font-weight: 600;
}

.result-icon.correct { color: #52c41a; }
.result-icon.wrong { color: #ff4d4f; }

/* 答案解析 */
.explanation-box {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.explanation-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.explanation-icon {
  font-size: 24px;
}

.explanation-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.explanation-text {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

/* 按钮 */
.action-buttons {
  display: flex;
  justify-content: center;
}

.btn {
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline {
  background: white;
  border: 1px solid #d9d9d9;
  color: #666;
}

.btn-outline:hover {
  border-color: #667eea;
  color: #667eea;
}

/* 结果页面 */
.result-content {
  padding: 32px;
  display: flex;
  justify-content: center;
}

.result-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  max-width: 700px;
  width: 100%;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 32px;
  margin-bottom: 32px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-circle.excellent { background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%); }
.score-circle.good { background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%); }
.score-circle.fair { background: linear-gradient(135deg, #fff7e6 0%, #ffd591 100%); }
.score-circle.poor { background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%); }

.score-value {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a1a;
}

.score-label {
  font-size: 14px;
  color: #666;
}

.result-summary h1 {
  margin: 0 0 12px 0;
  font-size: 28px;
  color: #1a1a1a;
}

.level-text {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #666;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
}

.level-badge.beginner { background: #f6ffed; color: #52c41a; }
.level-badge.intermediate { background: #e6f7ff; color: #1890ff; }
.level-badge.advanced { background: #fff2f0; color: #ff4d4f; }

.correct-text {
  margin: 0;
  font-size: 14px;
  color: #999;
}

/* 分类得分 */
.category-scores {
  margin-bottom: 28px;
}

.category-scores h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #1a1a1a;
}

.scores-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.score-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px 16px;
}

.score-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.category-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.category-score {
  font-size: 14px;
  color: #666;
  font-weight: 600;
}

.score-bar {
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s;
}

.score-fill.excellent { background: #52c41a; }
.score-fill.good { background: #1890ff; }
.score-fill.fair { background: #fa8c16; }
.score-fill.poor { background: #ff4d4f; }

/* 推荐 */
.recommendation-box {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 12px;
  margin-bottom: 28px;
}

.rec-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.rec-content h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #1a1a1a;
}

.rec-content p {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 结果操作 */
.result-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
