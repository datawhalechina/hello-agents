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
              <MarkdownRenderer :content="msg.content" />
            </div>
            <div v-else class="bubble user-bubble">{{ msg.content }}</div>
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
      <CodeEditor />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onActivated } from 'vue'
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

const autoResize = () => {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
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
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    messages.value.push({ 
      role: 'assistant', 
      content: `抱歉，出现了一些问题：${errorMsg}` 
    })
    agentStore.resetAllStatus()
  } finally {
    loading.value = false
    learningContext.value = null
    await scrollToBottom()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(() => {
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
  max-width: 100%;
  overflow: hidden;
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
</style>
