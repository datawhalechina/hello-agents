<template>
  <div class="app-container">
    <!-- 左侧对话区 -->
    <div class="chat-section">
      <div class="chat-header">
        <div class="header-left">
          <div class="avatar">
            <span>🤖</span>
          </div>
          <div class="header-info">
            <h2>Way_to_Engineer</h2>
            <span class="subtitle">{{ langStore.t('chat.subtitle') }}</span>
          </div>
        </div>
        <div class="status-badge">
          <span class="status-dot"></span>
          <span>{{ langStore.t('chat.online') }}</span>
        </div>
        <button class="clear-btn" @click="clearChat" title="清除对话历史">
          🗑️
        </button>
      </div>
      
      <div class="messages" ref="messagesContainer">
        <div class="welcome-card">
          <div class="welcome-icon">👋</div>
          <h3>{{ langStore.t('chat.welcomeTitle') }}</h3>
          <p>{{ langStore.t('chat.welcomeDesc') }}</p>
          <div class="feature-list">
            <div class="feature-item">
              <span class="feature-icon">👨‍🏫</span>
              <span>{{ langStore.t('chat.features.tutor') }}</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🐛</span>
              <span>{{ langStore.t('chat.features.debug') }}</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🔍</span>
              <span>{{ langStore.t('chat.features.review') }}</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🏗️</span>
              <span>{{ langStore.t('chat.features.arch') }}</span>
            </div>
          </div>
        </div>

        <div v-if="sessionData" class="session-banner">
          <div class="session-banner-content">
            <span class="session-banner-icon">👋</span>
            <div class="session-banner-text">
              <p>{{ langStore.t('chat.continueSession', { lesson: sessionData.lesson_title || '' }) }}</p>
            </div>
            <button class="btn btn-primary btn-sm" @click="continueSession">继续学习 →</button>
            <button class="session-dismiss" @click="sessionData = null">✕</button>
          </div>
        </div>
        
        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message', msg.role]"
        >
          <div v-if="msg.role === 'assistant'" class="msg-avatar" :class="'avatar-' + getAgentType(msg.agent_name)">
            {{ getAgentIcon(msg.agent_name) }}
          </div>
          <div class="msg-body">
            <div v-if="msg.agent_name" class="agent-tag" :class="'tag-' + getAgentType(msg.agent_name)">{{ msg.agent_name }}</div>
            <div v-if="msg.role === 'assistant'" class="bubble assistant-bubble">
              <MarkdownRenderer
                :content="msg.content"
                @quiz-result="(r) => onQuizResult(r, msg)"
                @exercise-detected="onExerciseDetected"
                @content-meta="(m) => onContentMeta(m, msg)"
              />
            </div>
            <div v-else class="bubble user-bubble">{{ msg.content }}</div>
            <div v-if="isLastAssistantMessage(index) && learningContext" class="mastered-section">
              <button class="mastered-btn" @click="masteredClick" :disabled="masteredLoading">
                <span v-if="!masteredLoading">{{ langStore.t('chat.masteredBtn') }}</span>
                <span v-else class="spinner"></span>
              </button>
            </div>
          </div>
          <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">👤</div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-body">
            <div class="bubble typing-bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Completion banner (between messages and input) -->
      <div v-if="completionData" class="completion-banner" :class="completionData.passed ? 'pass' : 'fail'">
        <div class="completion-content">
          <span class="completion-icon">{{ completionData.passed ? '🎉' : '💪' }}</span>
          <div class="completion-text">
            <p v-if="completionData.passed">
              {{ langStore.t('chat.quizPass', { correct: completionData.correct, total: completionData.total }) }}
            </p>
            <p v-else>
              {{ langStore.t('chat.quizFail', { correct: completionData.correct, total: completionData.total }) }}
            </p>
            <p v-if="completionData.lessonCompleted" class="lesson-complete">
              {{ langStore.t('chat.lessonCompleted') }}
            </p>
          </div>
          <button v-if="completionData.lessonCompleted" class="btn btn-primary btn-sm" @click="goNextLesson">
            {{ langStore.t('chat.nextLesson') }}
          </button>
          <button v-else class="btn btn-outline btn-sm" @click="completionData = null">
            {{ langStore.t('chat.close') }}
          </button>
        </div>
      </div>
      
      <div class="input-area">
        <div class="input-wrapper">
          <textarea 
            v-model="input" 
            rows="1"
            :placeholder="langStore.t('chat.placeholder')"
            @keydown.enter.exact.prevent="send"
            @input="autoResize"
            ref="textareaRef"
          ></textarea>
          <button class="send-btn" @click="send" :disabled="loading || !input.trim()">
            <span v-if="!loading">{{ langStore.t('chat.send') }}</span>
            <span v-else class="spinner"></span>
          </button>
        </div>
        <div class="input-hint">{{ langStore.t('chat.hint') }}</div>
      </div>
    </div>
    
    <!-- 右侧代码区 -->
    <div class="code-section">
      <CodeEditor :exerciseData="currentExercise" @exercise-submitted="onExerciseSubmitted" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onActivated } from 'vue'
import axios from 'axios'
import CodeEditor from '../components/CodeEditor.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import { useAgentStore } from '../stores/agentStore'
import { useAuthStore } from '../stores/authStore'
import { useLangStore } from '../stores/langStore'
import { getAgentIcon, getAgentType } from '../utils/helpers'

interface Message {
  role: 'user' | 'assistant'
  content: string
  agent_name?: string
}

const agentStore = useAgentStore()
const authStore = useAuthStore()
const langStore = useLangStore()
const messages = ref<Message[]>([])
const input = ref('')
const loading = ref(false)
const messagesContainer = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()

const sessionData = ref<any>(null)
const masteredLoading = ref(false)
const completionData = ref<{ passed: boolean; correct: number; total: number; lessonCompleted: boolean } | null>(null)
const nextLessonData = ref<{ id: string; title: string; description: string; module_title: string; module_id: string; path_type?: string } | null>(null)
const currentExercise = ref<{ code: string; language: string; lessonId?: string | null } | null>(null)

// 练习追踪
const pendingExerciseCount = ref(0)        // 当前消息中待完成的练习数
const completedExerciseCount = ref(0)       // 已完成的练习数

const autoResize = () => {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
}

const isLastAssistantMessage = (index: number) => {
  if (index !== messages.value.length - 1) return false
  return messages.value[index].role === 'assistant'
}

const clearChat = () => {
  if (messages.value.length === 0) return
  if (confirm('确定清除所有对话记录吗？此操作不可恢复。')) {
    messages.value = []
  }
}

const send = async (context?: Record<string, any>) => {
  const text = input.value.trim()
  
  if (!text || loading.value) return

  // 发送新消息时清理练习模式
  currentExercise.value = null
  
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  
  // 重置textarea高度
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
  
  await scrollToBottom()
  
  try {
    const payload: Record<string, any> = {
      message: text,
      user_id: authStore.userId,
    }
    if (context) {
      payload.context = context
    }
    
    const response = await axios.post('/api/chat/', payload)
    
    const agentName = response.data.agent_name
    const agentType = getAgentType(agentName)
    
    // 更新Agent状态
    agentStore.setActiveAgent(agentType)
    
    messages.value.push({ 
      role: 'assistant', 
      content: response.data.reply,
      agent_name: agentName 
    })
    
    // 记录消息
    agentStore.recordMessage(agentType, response.data.reply)
    agentStore.resetAllStatus()
    
    // 保存学习会话（带最新回复摘要）
    if (learningContext.value) {
      saveSession(response.data.reply)
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    messages.value.push({ 
      role: 'assistant', 
      content: `抱歉，出现了一些问题：${errorMsg}` 
    })
    agentStore.resetAllStatus()
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(async () => {
  // Load saved session
  try {
    const sessionRes = await axios.get('/api/learning/session', {
      params: { user_id: authStore.userId }
    })
    const sess = sessionRes.data.session
    if (sess && sess.lesson_id) {
      sessionData.value = sess
    }
  } catch (e) {
    console.error('Failed to load session:', e)
  }

  checkPendingMessage()
})

onActivated(() => {
  checkPendingMessage()
})

// 学习上下文
const learningContext = ref<any>(null)

const checkPendingMessage = () => {
  // 优先读取新的上下文格式
  const pendingContext = sessionStorage.getItem('pendingLearningContext')
  if (pendingContext) {
    sessionStorage.removeItem('pendingLearningContext')
    try {
      const context = JSON.parse(pendingContext)
      learningContext.value = context
      input.value = context.message
      saveSession() // 保存学习会话到后端
      // 延迟确保DOM更新后再发送
      setTimeout(() => {
        send(context)
      }, 100)
      return
    } catch (e) {
      console.error('Failed to parse learning context:', e)
    }
  }
  
  // 兼容旧格式
  const pendingMessage = sessionStorage.getItem('pendingLearningMessage')
  if (pendingMessage) {
    sessionStorage.removeItem('pendingLearningMessage')
    input.value = pendingMessage
    // 延迟确保DOM更新后再发送
    setTimeout(() => {
      send()
    }, 100)
  }
}

const saveSession = async (summary?: string) => {
  if (!learningContext.value) return
  try {
    await axios.post('/api/learning/session', {
      lesson_id: learningContext.value.lesson_id,
      module_id: learningContext.value.module_id,
      lesson_title: learningContext.value.lesson_title,
      module_title: learningContext.value.module_title,
      path_type: learningContext.value.path_type,
      last_reply_summary: summary || '',
    }, { params: { user_id: authStore.userId } })
  } catch (e) {
    // 静默失败，不影响用户体验
  }
}

const clearSession = async () => {
  try {
    await axios.post('/api/learning/session', {}, { params: { user_id: authStore.userId, clear: true } })
  } catch (e) { /* ignore */ }
}

const continueSession = async () => {
  if (!sessionData.value) return
  const ctx = {
    message: `我想继续学习"${sessionData.value.lesson_title}"这个课程。请帮我讲解这个主题。`,
    path_type: sessionData.value.path_type,
    lesson_id: sessionData.value.lesson_id,
    module_id: sessionData.value.module_id,
    lesson_title: sessionData.value.lesson_title,
    module_title: sessionData.value.module_title,
  }
  learningContext.value = ctx
  input.value = ctx.message
  sessionData.value = null
  await saveSession()
  setTimeout(() => send(ctx), 100)
}

const masteredClick = async () => {
  if (!learningContext.value || masteredLoading.value) return
  masteredLoading.value = true
  
  const quizMsg = `我已完成"${learningContext.value.lesson_title || ''}"的学习。作为编程导师，请出 2-3 道测验题检验我的理解，请严格按照以下格式：
1. 选择题使用 \`\`\`quiz JSON 格式
2. 代码练习题使用 \`\`\`exercise:python（或对应的语言）格式，题目作为注释写在代码里，留出填空位让用户自己写代码
3. 题目难度匹配我当前的水平
4. 对于代码练习题，请给出操作指引告诉用户：「请点击「📂 在编辑器中打开」按钮，在右侧编辑器中补全代码，然后点击「📝 提交练习反馈」获取批改和优化建议」。不要写「告诉我你的答案」或「在代码注释填空」等与实际操作不符的指引`
  
  try {
    const res = await axios.post('/api/chat/', {
      message: quizMsg,
      context: learningContext.value,
    })
    messages.value.push({
      role: 'assistant',
      content: res.data.reply,
      agent_name: res.data.agent_name,
    })
    await scrollToBottom()
  } catch (err: any) {
    messages.value.push({
      role: 'assistant',
      content: `抱歉，出题失败：${err.message}`
    })
  } finally {
    masteredLoading.value = false
  }
}

const checkLessonComplete = (quizResult?: { correct: number; total: number }) => {
  // 有练习时要求全部提交完成
  if (pendingExerciseCount.value > 0 && completedExerciseCount.value < pendingExerciseCount.value) {
    return
  }
  const lessonId = learningContext.value?.lesson_id
  if (!lessonId) return
  
  axios.post(`/api/learning/complete-lesson/${lessonId}`, null, {
    params: { user_id: authStore.userId }
  }).then((res) => {
    // 保存下一课程信息（包含 path_type）
    const next = res.data?.next_lesson
    if (next) {
      nextLessonData.value = {
        ...next,
        path_type: learningContext.value?.path_type,
      }
    } else {
      nextLessonData.value = null
    }
    completionData.value = {
      passed: true,
      correct: quizResult?.correct || 0,
      total: quizResult?.total || 0,
      lessonCompleted: true,
    }
    learningContext.value = null
    clearSession()
  }).catch(e => {
    console.error('Failed to complete lesson:', e)
    completionData.value = {
      passed: true,
      correct: quizResult?.correct || 0,
      total: quizResult?.total || 0,
      lessonCompleted: false,
    }
  })
}

const onQuizResult = (result: { total: number; correct: number }) => {
  if (!learningContext.value) return
  
  const passed = result.correct / result.total >= 0.6
  
  if (passed && result.total >= 2) {
    if (pendingExerciseCount.value > 0 && completedExerciseCount.value < pendingExerciseCount.value) {
      // 有练习未完成，暂存结果但不等完成
      completionData.value = {
        passed: true,
        correct: result.correct,
        total: result.total,
        lessonCompleted: false,
      }
    } else {
      // 无练习 或 练习已全部提交 → 直接完成
      checkLessonComplete(result)
    }
  } else if (passed && result.total < 2) {
    completionData.value = null
  } else {
    completionData.value = {
      passed: false,
      correct: result.correct,
      total: result.total,
      lessonCompleted: false,
    }
  }
}

const onContentMeta = (meta: { quizCount: number; exerciseCount: number }, msg: any) => {
  // 记录练习数，用于完成判定
  pendingExerciseCount.value = meta.exerciseCount
}
const onExerciseSubmitted = (result: { feedback: string }) => {
  completedExerciseCount.value++
  
  // 所有练习完成 & 选择题已通过 → 完成课程
  if (completedExerciseCount.value >= pendingExerciseCount.value && learningContext.value) {
    if (completionData.value?.passed && !completionData.value.lessonCompleted) {
      checkLessonComplete({
        correct: completionData.value.correct,
        total: completionData.value.total,
      })
    }
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) saveSession(lastMsg.content)
  }
}

const onExerciseDetected = (data: { code: string; language: string }) => {
  currentExercise.value = {
    code: data.code,
    language: data.language,
    lessonId: learningContext.value?.lesson_id || null,
  }
}

const goNextLesson = () => {
  const next = nextLessonData.value
  completionData.value = null
  nextLessonData.value = null

  if (!next || !next.path_type) {
    // 没有下一课信息 → 回到学习路径页
    window.location.hash = '#/learning'
    return
  }

  // 自动启动下一课：设置学习上下文并发消息给导师
  const ctx = {
    message: `请开始讲解"${next.title}"。这是下一节课的内容，请详细讲解。`,
    path_type: next.path_type,
    lesson_id: next.id,
    module_id: next.module_id,
    lesson_title: next.title,
    module_title: next.module_title,
  }
  learningContext.value = ctx
  input.value = ctx.message
  saveSession(ctx.message)
  // 延迟发送确保 DOM 更新
  setTimeout(() => send(ctx), 100)
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex: 1;
  background: #f8f9fa;
  overflow: hidden;
}

.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e5e5e5;
}

.code-section {
  width: 550px;
  padding: 16px;
  background: #1e1e1e;
  overflow: hidden;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.header-info h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  font-size: 13px;
  opacity: 0.85;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.2);
  border-radius: 20px;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #52c41a;
  animation: pulse 2s infinite;
}

.clear-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  margin-left: 8px;
  flex-shrink: 0;
}

.clear-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.clear-btn:active {
  transform: scale(0.95);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  margin-bottom: 16px;
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.welcome-card h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #1a1a1a;
}

.welcome-card p {
  margin: 0 0 16px 0;
  color: #666;
  font-size: 14px;
}

.feature-list {
  display: flex;
  justify-content: center;
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border-radius: 8px;
  font-size: 13px;
  color: #333;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.feature-icon {
  font-size: 16px;
}

/* Message Bubble */
.message {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.avatar-tutor {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.avatar-debug {
  background: linear-gradient(135deg, #f5222d 0%, #cf1322 100%);
}

.avatar-review {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
}

.avatar-arch {
  background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%);
}

.avatar-coach {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
}

.user-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.agent-tag {
  font-size: 11px;
  color: #999;
  padding-left: 4px;
}

.tag-tutor { color: #667eea; }
.tag-debug { color: #f5222d; }
.tag-review { color: #52c41a; }
.tag-arch { color: #fa8c16; }
.tag-coach { color: #722ed1; }

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
}

.message.user .bubble {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .bubble {
  background: #f0f2f5;
  color: #1a1a1a;
  border-bottom-left-radius: 4px;
}

.assistant-bubble {
  width: 100%;
  min-width: 0;
}

.user-bubble {
  white-space: pre-wrap;
}

/* Typing Animation */
.typing-bubble {
  display: flex;
  gap: 4px;
  padding: 16px 20px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Input Area */
.input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e5e5e5;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 8px 12px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.input-wrapper:focus-within {
  border-color: #667eea;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.input-wrapper textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  padding: 8px 4px;
  font-family: inherit;
}

.input-wrapper textarea:focus {
  outline: none;
}

.send-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  min-width: 80px;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #999;
  text-align: center;
}

/* Session banner */
.session-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 16px;
  animation: slideUp 0.3s ease;
}

.session-banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-banner-icon { font-size: 24px; }

.session-banner-text { flex: 1; }

.session-banner-text p { margin: 0; color: white; font-size: 14px; line-height: 1.5; }

.session-dismiss {
  background: none; border: none; color: rgba(255,255,255,0.6);
  font-size: 18px; cursor: pointer; padding: 4px;
}

.session-dismiss:hover { color: white; }

/* Mastered button */
.mastered-section { margin-top: 8px; text-align: right; }

.mastered-btn {
  padding: 8px 20px; background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  color: white; border: none; border-radius: 20px; cursor: pointer;
  font-size: 14px; font-weight: 500; transition: all 0.2s;
}

.mastered-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4); }

.mastered-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* Completion banner */
.completion-banner {
  border-radius: 12px; padding: 16px 20px; margin: 0 24px 8px; animation: fadeIn 0.3s;
  flex-shrink: 0;
}

.completion-banner.pass { background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%); border: 1px solid #b7eb8f; }

.completion-banner.fail { background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%); border: 1px solid #ffccc7; }

.completion-content { display: flex; align-items: center; gap: 12px; }

.completion-icon { font-size: 28px; }

.completion-text { flex: 1; }

.completion-text p { margin: 0; font-size: 14px; color: #333; line-height: 1.5; }

.completion-text .lesson-complete { color: #52c41a; font-weight: 600; margin-top: 4px; }

/* Button utilities */
.btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; display: inline-flex; align-items: center; gap: 6px; }
.btn-sm { padding: 6px 14px; font-size: 13px; }

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white; border: none; border-radius: 8px; cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }

.btn-outline {
  background: transparent; color: #667eea; border: 1px solid #667eea;
  border-radius: 8px; cursor: pointer; transition: all 0.2s;
}

.btn-outline:hover { background: rgba(102, 126, 234, 0.05); }

/* Animations */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

@keyframes slideUp { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
