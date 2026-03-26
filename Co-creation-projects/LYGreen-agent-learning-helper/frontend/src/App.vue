<script lang="ts" setup>
import { ref, computed, reactive, watch, onMounted } from 'vue'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:3000'
const STORAGE_KEY = 'ai_learning_journey_state' // 本地存储的 Key

interface Feedback {
  content: string
  can_pass: boolean
}

interface QAndA {
  question: string
  user_answer?: string
  feedback?: Feedback
}

interface Step {
  title: string
  description: string
  content: string
  qAndA?: QAndA
}

interface Response {
  result: string
  data: any
}

// ==== 状态变量 ====
const subject = ref<string>('')
const hasGenerated = ref<boolean>(false)
const isGenerating = ref<boolean>(false)
const generationProgress = ref<number>(0)
const loadingMessage = ref<string>('正在构建知识图谱...')

const learningPath = ref<Step[]>([])
const currentStepIndex = ref<number>(0)
const userAnswer = ref<string>('')
const isSubmitting = ref<boolean>(false)
const feedback = reactive<Feedback>({ content: '', can_pass: false })
const unlockedSteps = ref<number>(0)
const isFinished = ref<boolean>(false) // 新增：是否已完成所有关卡

// ==== 计算属性 ====
const currentStep = computed<Step | undefined>(() => learningPath.value[currentStepIndex.value])
const isCurrentStepCompleted = computed<boolean>(() => unlockedSteps.value > currentStepIndex.value)

// ==== 本地存储逻辑 ====
const saveState = () => {
  // 只有在生成内容后才保存，避免保存空状态
  if (!hasGenerated.value) return 
  const state = {
    subject: subject.value,
    hasGenerated: hasGenerated.value,
    learningPath: learningPath.value,
    currentStepIndex: currentStepIndex.value,
    unlockedSteps: unlockedSteps.value,
    isFinished: isFinished.value
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

const loadState = () => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const state = JSON.parse(saved)
      subject.value = state.subject
      hasGenerated.value = state.hasGenerated
      learningPath.value = state.learningPath
      currentStepIndex.value = state.currentStepIndex
      unlockedSteps.value = state.unlockedSteps
      isFinished.value = state.isFinished || false
      
      if (hasGenerated.value && !isFinished.value) {
        restoreStepState()
      }
    } catch (e) {
      console.error('读取学习进度缓存失败:', e)
    }
  }
}

// 页面加载时恢复状态
onMounted(() => {
  loadState()
})

// 监听核心状态变化，自动保存
watch(
  [subject, hasGenerated, learningPath, currentStepIndex, unlockedSteps, isFinished], 
  saveState, 
  { deep: true }
)

// ==== 核心方法 ====
const startGeneration = async () => {
  if (!subject.value.trim()) return

  isGenerating.value = true
  generationProgress.value = 0
  loadingMessage.value = '正在检索核心概念...'

  const interval = setInterval(() => {
    generationProgress.value += Math.floor(Math.random() * 10) + 5
    if (generationProgress.value > 30) loadingMessage.value = '正在编排打怪升级路线...'
    if (generationProgress.value > 70) loadingMessage.value = '即将完成...'
    
    if (generationProgress.value >= 99) {
      generationProgress.value = 99
      clearInterval(interval)
    }
  }, 1000)

  try {
    const response = await fetch(`${BACKEND_URL}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: '/generate',
        data: { subject: subject.value }
      })
    })

    const json = await response.json() as Response
    const data = json.data as { steps: { title: string, description: string, content: string }[] }

    clearInterval(interval)

    learningPath.value = data.steps.map(step => ({ ...step, qAndA: undefined }))
    await generateQuestion()
    
    generationProgress.value = 100
    setTimeout(() => {
      isGenerating.value = false
      hasGenerated.value = true
    }, 500)
  } catch (err) {
    console.error(err)
    clearInterval(interval)
    loadingMessage.value = '网络请求失败，请检查后端服务'
    setTimeout(() => { isGenerating.value = false }, 2000)
  }
}

const generateQuestion = async () => {
  if (!currentStep.value) return
  
  try {
    const response = await fetch(`${BACKEND_URL}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: '/generate_question',
        data: {
          subject: subject.value,
          title: currentStep.value.title,
          description: currentStep.value.description,
          content: currentStep.value.content
        }
      })
    })

    const json = await response.json() as Response
    
    (learningPath.value[currentStepIndex.value] as any).qAndA = {
      question: json.data.question
    }
  } catch (error) {
    console.error(error);
    (learningPath.value[currentStepIndex.value] as any).qAndA = {
      question: '随堂测试加载失败，请思考：这段内容的核心知识点是什么？'
    }
  }
}

const submitAnswer = async () => {
  const step = currentStep.value
  if (!userAnswer.value.trim() || isSubmitting.value || isCurrentStepCompleted.value || !step || !step.qAndA) return

  isSubmitting.value = true
  feedback.content = '正在批改中...'
  feedback.can_pass = false

  try {
    const response = await fetch(`${BACKEND_URL}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: '/check_answer',
        data: {
          subject: subject.value,
          question: step.qAndA.question,
          user_answer: userAnswer.value 
        }
      })
    })

    const json = await response.json() as Response
    feedback.content = json.data.content
    feedback.can_pass = json.data.can_pass
    
    if (feedback.can_pass) {
      unlockedSteps.value = Math.max(unlockedSteps.value, currentStepIndex.value + 1)
      step.qAndA.user_answer = userAnswer.value
      step.qAndA.feedback = { content: feedback.content, can_pass: feedback.can_pass }
    }
  } catch (err) {
    console.error(err)
    feedback.content = '网络异常，请重试'
  } finally {
    isSubmitting.value = false
  }
}

const restoreStepState = () => {
  const step = currentStep.value
  if (step?.qAndA?.feedback) {
    userAnswer.value = step.qAndA.user_answer || ''
    feedback.content = step.qAndA.feedback.content
    feedback.can_pass = step.qAndA.feedback.can_pass
  } else {
    userAnswer.value = ''
    feedback.content = ''
    feedback.can_pass = false
  }
}

const prevStep = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
    restoreStepState()
  }
}

const nextStep = async () => {
  if (currentStepIndex.value < learningPath.value.length - 1 && isCurrentStepCompleted.value) {
    currentStepIndex.value++
    restoreStepState()
    
    if (!currentStep.value?.qAndA) {
      await generateQuestion()
    }
  }
}

// ==== 流程结束与重置 ====
const finishJourney = () => {
  isFinished.value = true
}

const resetJourney = () => {
  // 清除本地缓存，并重置所有状态
  localStorage.removeItem(STORAGE_KEY)
  subject.value = ''
  hasGenerated.value = false
  isGenerating.value = false
  learningPath.value = []
  currentStepIndex.value = 0
  unlockedSteps.value = 0
  isFinished.value = false
  userAnswer.value = ''
  feedback.content = ''
  feedback.can_pass = false
}
</script>

<template>
  <div class="app-container">
    <div class="card">
      
      <div v-if="!hasGenerated && !isGenerating && !isFinished" class="init-section fade-in">
        <div class="hero-icon">
          <svg viewBox="0 0 24 24" width="80" height="80" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <h1 class="main-title">AI 专属学习路线</h1>
        <p class="subtitle">告诉我你想学什么，为你规划结构化的闯关指南</p>
        
        <div class="input-group">
          <input 
            id="subject" 
            v-model="subject" 
            type="text" 
            placeholder="例如：Vue3, TypeScript, 离散数学..." 
            @keyup.enter="startGeneration"
          />
          <button class="primary-btn pulse-hover" @click="startGeneration" :disabled="!subject.trim()">
            🚀 开启旅程
          </button>
        </div>
      </div>

      <div v-if="isGenerating" class="progress-section fade-in">
        <h3 class="loading-title">正在为你量身定制《{{ subject }}》...</h3>
        <p class="loading-msg">{{ loadingMessage }}</p>
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: generationProgress + '%' }"></div>
        </div>
      </div>

      <div v-if="hasGenerated && learningPath.length > 0 && !isFinished" class="learning-section fade-in">
        <div class="header-info">
          <h2>📚 {{ subject }}</h2>
          <div class="step-tracker">
            <div 
              v-for="(step, index) in learningPath" 
              :key="index"
              class="tracker-dot"
              :class="{ 
                'active': index === currentStepIndex, 
                'completed': index < unlockedSteps 
              }"
            ></div>
          </div>
        </div>

        <div class="step-card">
          <div class="step-badge">第 {{ currentStepIndex + 1 }} 关</div>
          <h3 class="step-title">{{ currentStep?.title }}</h3>
          <p class="step-desc">{{ currentStep?.description }}</p>
          <div class="step-content">{{ currentStep?.content }}</div>

          <div class="question-box" v-if="currentStep && currentStep.qAndA">
            <h4 class="q-title">🧠 随堂测试（通关条件）</h4>
            <p class="question-text">{{ currentStep.qAndA?.question }}</p>

            <div class="answer-group">
              <textarea 
                v-model="userAnswer" 
                placeholder="输入你的理解... (Enter 提交，Shift + Enter 换行)" 
                :disabled="isSubmitting || isCurrentStepCompleted"
                @keydown.enter.exact.prevent="submitAnswer"
                rows="2"
              ></textarea>
              <button 
                @click="submitAnswer" 
                class="submit-btn"
                :class="{ 'success-btn': isCurrentStepCompleted }"
                :disabled="isSubmitting || isCurrentStepCompleted || !userAnswer.trim()"
              >
                <span v-if="isSubmitting">思考中...</span>
                <span v-else-if="isCurrentStepCompleted">✨ 验证通过</span>
                <span v-else>提交验证</span>
              </button>
            </div>

            <transition name="slide-fade">
              <div v-if="feedback.content" :class="['feedback-card', feedback.can_pass ? 'success' : 'error']">
                {{ feedback.content }}
              </div>
            </transition>
          </div>
        </div>

        <div class="navigation-buttons">
          <button class="nav-btn" @click="prevStep" :disabled="currentStepIndex === 0">
            ← 上一步
          </button>
          
          <button 
            v-if="currentStepIndex < learningPath.length - 1"
            class="nav-btn primary-btn" 
            @click="nextStep" 
            :disabled="!isCurrentStepCompleted"
          >
            下一步 →
          </button>
          <button 
            v-else
            class="nav-btn success-btn" 
            @click="finishJourney" 
            :disabled="!isCurrentStepCompleted"
          >
            🎉 完成旅程
          </button>
        </div>
      </div>
      
      <div v-if="isFinished" class="finish-section fade-in">
        <div class="hero-icon trophy-icon">🏆</div>
        <h1 class="main-title">恭喜通关！</h1>
        <p class="subtitle">你已成功掌握了《{{ subject }}》的核心知识点，太棒了！</p>
        <button class="primary-btn pulse-hover" @click="resetJourney">
          返回初始界面，开启新探索
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* 保持原有样式不变，追加以下新样式 */

.app-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--bg-color);
  background-image: radial-gradient(#e0e6ed 1px, transparent 1px);
  background-size: 20px 20px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  padding: 20px;
}

.card {
  width: 100%;
  max-width: 680px;
  background: var(--card-bg);
  padding: 40px;
  border-radius: var(--border-radius);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
}

.init-section {
  text-align: center;
  padding: 20px 0;
}
.hero-icon {
  color: var(--primary);
  margin-bottom: 20px;
  animation: float 3s ease-in-out infinite;
}
.main-title {
  color: var(--text-main);
  font-size: 28px;
  margin-bottom: 10px;
}
.subtitle {
  color: var(--text-sub);
  margin-bottom: 30px;
  font-size: 15px;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-width: 400px;
  margin: 0 auto;
}

input, textarea {
  padding: 14px 16px;
  border: 2px solid #dfe6e9;
  border-radius: 12px;
  font-size: 16px;
  transition: all 0.2s;
  background: #fafbfc;
  font-family: inherit;
}

input:focus, textarea:focus {
  outline: none;
  border-color: var(--primary);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(108, 92, 231, 0.1);
}

input:disabled, textarea:disabled {
  background-color: #f5f6fa;
  cursor: not-allowed;
  color: #a4b0be;
}

textarea {
  resize: vertical; 
  min-height: 52px;
  line-height: 1.5;
}

button {
  padding: 14px 24px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.primary-btn {
  background-color: var(--primary);
  color: white;
}
.primary-btn:hover:not(:disabled) {
  background-color: var(--primary-hover);
  transform: translateY(-1px);
}
.nav-btn {
  background-color: #f1f2f6;
  color: var(--text-main);
  flex: 1;
}
.nav-btn:hover:not(:disabled) {
  background-color: #dfe4ea;
}

.progress-section {
  text-align: center;
  padding: 40px 0;
}
.loading-title {
  color: var(--text-main);
  margin-bottom: 10px;
}
.loading-msg {
  color: var(--text-sub);
  font-size: 14px;
}
.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: #f1f2f6;
  border-radius: 10px;
  overflow: hidden;
  margin: 25px 0;
}
.progress-bar {
  height: 100%;
  background-color: var(--primary);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.header-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}
.header-info h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 22px;
}
.step-tracker {
  display: flex;
  gap: 8px;
}
.tracker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #dfe6e9;
  transition: all 0.3s;
}
.tracker-dot.completed { background: var(--success); }
.tracker-dot.active { background: var(--primary); transform: scale(1.3); }

.step-card {
  background-color: #fafbfc;
  padding: 30px;
  border-radius: var(--border-radius);
  border: 1px solid #f1f2f6;
  margin-bottom: 25px;
  position: relative;
}
.step-badge {
  position: absolute;
  top: -12px;
  left: 30px;
  background: var(--primary);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
}
.step-title {
  color: var(--text-main);
  margin: 10px 0 5px 0;
  font-size: 20px;
}
.step-desc {
  color: var(--text-sub);
  font-style: italic;
  font-size: 14px;
  margin-bottom: 15px;
}
.step-content {
  color: var(--text-main);
  line-height: 1.7;
  font-size: 15.5px;
  white-space: pre-wrap; 
}

.question-box {
  margin-top: 30px;
  padding-top: 25px;
  border-top: 2px dashed #dfe6e9;
}
.q-title {
  color: var(--text-main);
  margin-top: 0;
}
.question-text {
  font-weight: 500;
  color: var(--primary);
  background: rgba(108, 92, 231, 0.05);
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid var(--primary);
  white-space: pre-wrap; 
}
.answer-group {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  align-items: flex-start; 
}

.answer-group input, 
.answer-group textarea {
  flex: 1;
}

.submit-btn {
  background-color: var(--text-main);
  color: white;
  min-width: 120px;
  height: 52px; 
  display: flex;
  align-items: center;
  justify-content: center;
}
.submit-btn:hover:not(:disabled) {
  background-color: #000;
}
.success-btn {
  background-color: var(--success) !important;
  color: white;
}

.feedback-card {
  margin-top: 20px;
  padding: 15px;
  border-radius: 8px;
  font-weight: 500;
  line-height: 1.5;
  white-space: pre-wrap; 
}
.feedback-card.success { 
  background-color: rgba(0, 184, 148, 0.1);
  color: #00947a;
  border: 1px solid rgba(0, 184, 148, 0.2);
}
.feedback-card.error { 
  background-color: rgba(255, 118, 117, 0.1);
  color: #d63031;
  border: 1px solid rgba(255, 118, 117, 0.2);
}

.navigation-buttons {
  display: flex;
  gap: 15px;
}

/* ==== 新增：通关祝贺界面样式 ==== */
.finish-section {
  text-align: center;
  padding: 40px 0;
}
.trophy-icon {
  font-size: 72px; /* emoji 放大 */
  line-height: 1;
  margin-bottom: 20px;
  animation: bounce 2s infinite;
}

/* 动画效果 */
@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-15px); }
}
.fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}
</style>