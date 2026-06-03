<template>
  <div class="chat-container">
    <!-- 侧边栏：会话列表 -->
    <div class="chat-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="sidebar-title" v-show="!sidebarCollapsed">
          <span class="sidebar-icon">💬</span>
          <span>旅游AI对话</span>
        </div>
        <a-button
          type="primary"
          class="new-chat-btn"
          @click="createNewSession"
          :title="sidebarCollapsed ? '新建对话' : ''"
        >
          <template #icon><PlusOutlined /></template>
          <span v-if="!sidebarCollapsed">新建对话</span>
        </a-button>
      </div>

      <div class="session-list">
        <a-spin :spinning="sessionsLoading" size="small">
          <a-empty
            v-if="!sessionsLoading && sessions.length === 0"
            :description="sidebarCollapsed ? '' : '暂无对话'"
            style="color: rgba(255,255,255,0.5);"
          />

          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: currentSessionId === session.id }"
            @click="switchSession(session.id)"
          >
            <div class="session-info" v-show="!sidebarCollapsed">
              <div class="session-title">{{ session.title }}</div>
              <div class="session-time">{{ formatTime(session.updated_at) }}</div>
            </div>
            <div class="session-actions" v-show="!sidebarCollapsed">
              <a-popconfirm
                title="确定删除这个对话？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="deleteSession(session.id)"
              >
                <a-button
                  size="small"
                  type="text"
                  danger
                  @click.stop
                >
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-popconfirm>
            </div>
            <!-- 折叠状态下只显示图标 -->
            <div class="session-icon-collapsed" v-show="sidebarCollapsed">
              💬
            </div>
          </div>
        </a-spin>
      </div>

      <!-- 折叠/展开按钮 -->
      <div class="sidebar-collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
        <MenuFoldOutlined v-if="!sidebarCollapsed" />
        <MenuUnfoldOutlined v-else />
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="chat-main">
      <!-- 消息区域 -->
      <div class="messages-container" ref="messagesContainer" @scroll="handleScroll">
        <!-- 欢迎提示 -->
        <div v-if="!currentSessionId" class="welcome-section">
          <div class="welcome-icon">🌍</div>
          <h2 class="welcome-title">旅游AI顾问</h2>
          <p class="welcome-desc">我是您的专属旅行规划助手，可以帮您解答任何旅行问题！</p>
          <div class="welcome-suggestions">
            <div class="suggestion-item" @click="quickQuestion('去北京旅游有什么必去的景点？')">
              <span class="suggestion-icon">🏛️</span>
              <span>北京必去景点</span>
            </div>
            <div class="suggestion-item" @click="quickQuestion('两个人去三亚旅游3天大概需要多少钱？')">
              <span class="suggestion-icon">💰</span>
              <span>三亚3天预算</span>
            </div>
            <div class="suggestion-item" @click="quickQuestion('带孩子去上海迪士尼有什么注意事项？')">
              <span class="suggestion-icon">🎢</span>
              <span>迪士尼攻略</span>
            </div>
            <div class="suggestion-item" @click="quickQuestion('成都美食有哪些推荐？')">
              <span class="suggestion-icon">🍜</span>
              <span>成都美食推荐</span>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-if="currentSessionId">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message-item"
            :class="msg.role"
          >
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="message-content">
              <div class="message-bubble">
                <div class="message-text">{{ msg.content }}</div>
              </div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
            </div>
          </div>

          <!-- AI思考中 -->
          <div v-if="isLoading" class="message-item assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="message-bubble thinking-bubble">
                <div class="thinking-dots">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <span class="thinking-text">思考中...</span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 输入区域 -->
      <div class="input-area" v-if="isLoggedIn">
        <div class="input-wrapper">
          <a-textarea
            v-model:value="inputMessage"
            placeholder="请输入您的旅行问题..."
            :rows="1"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            @pressEnter="onPressEnter"
            :disabled="isLoading"
            class="chat-input"
            ref="inputRef"
          />
          <a-button
            type="primary"
            class="send-btn"
            :loading="isLoading"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          >
            <template #icon><SendOutlined /></template>
          </a-button>
        </div>
        <div class="input-hint">
          按 Enter 发送消息，AI只回答与旅游相关的问题
        </div>
      </div>

      <!-- 未登录提示 -->
      <div class="input-area" v-else>
        <div class="login-tip">
          <a-button type="primary" @click="goLogin">请先登录后使用AI对话功能</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  DeleteOutlined,
  SendOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<any>(null)

const isLoggedIn = ref(false)
const sessions = ref<any[]>([])
const currentSessionId = ref<number | null>(null)
const messages = ref<any[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const sessionsLoading = ref(false)
const sidebarCollapsed = ref(false)

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://localhost:8000'

/** Cookie 自动携带 token */
async function api(path: string, options: RequestInit = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
}

function goLogin() {
  router.push('/login')
}

function formatTime(timeStr: string): string {
  if (!timeStr) return ''
  try {
    const d = new Date(timeStr)
    const now = new Date()
    const isToday = d.toDateString() === now.toDateString()
    const pad = (n: number) => String(n).padStart(2, '0')
    const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`
    if (isToday) return time
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    if (d.toDateString() === yesterday.toDateString()) return `昨天 ${time}`
    return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${time}`
  } catch {
    return timeStr
  }
}

/** 检查登录状态 */
async function checkAuth() {
  try {
    const res = await api('/api/auth/profile')
    isLoggedIn.value = res.ok
    if (res.ok) {
      fetchSessions()
    }
  } catch {
    isLoggedIn.value = false
  }
}

/** 获取会话列表 */
async function fetchSessions() {
  sessionsLoading.value = true
  try {
    const res = await api('/api/chat/sessions')
    const data = await res.json()
    if (data.success) {
      sessions.value = data.sessions || []
    }
  } catch (e) {
    console.error('获取会话列表失败:', e)
  } finally {
    sessionsLoading.value = false
  }
}

/** 创建新会话 */
async function createNewSession() {
  if (!isLoggedIn.value) {
    message.warning('请先登录')
    return
  }
  try {
    const res = await api('/api/chat/sessions', { method: 'POST' })
    const data = await res.json()
    if (data.success && data.session) {
      sessions.value.unshift(data.session)
      currentSessionId.value = data.session.id
      messages.value = []
      await nextTick()
      focusInput()
    }
  } catch (e) {
    message.error('创建会话失败')
  }
}

/** 切换会话 */
async function switchSession(sessionId: number) {
  if (sessionId === currentSessionId.value) return
  currentSessionId.value = sessionId
  messages.value = []
  isLoading.value = false
  await fetchMessages(sessionId)
  await nextTick()
  scrollToBottom()
  focusInput()
}

/** 获取消息列表 */
async function fetchMessages(sessionId: number) {
  try {
    const res = await api(`/api/chat/sessions/${sessionId}/messages`)
    const data = await res.json()
    if (data.success) {
      messages.value = data.messages || []
      await nextTick()
      scrollToBottom()
    }
  } catch (e) {
    console.error('获取消息失败:', e)
  }
}

/** 删除会话 */
async function deleteSession(sessionId: number) {
  try {
    const res = await api(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' })
    if (res.ok) {
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        messages.value = []
      }
      message.success('会话已删除')
    }
  } catch {
    message.error('删除失败')
  }
}

/** 处理回车键（在 Ant Design 的 keydown 中阻止换行插入） */
function onPressEnter(e: KeyboardEvent) {
  e.preventDefault()
  sendMessage()
}

/** 发送消息（流式SSE） */
async function sendMessage() {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value || !currentSessionId.value) return

  // 先显示用户消息
  const userMsg = {
    id: Date.now() + 1,
    session_id: currentSessionId.value,
    role: 'user',
    content: content,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)

  // === 立即清空输入框 ===
  inputMessage.value = ''
  // 直接操作 DOM + 触发 input 事件，确保 Ant Design 内部状态同步
  const ta = document.querySelector('.chat-input textarea') as HTMLTextAreaElement | null
  if (ta) {
    ta.value = ''
    ta.dispatchEvent(new Event('input', { bubbles: true }))
  }

  isLoading.value = true

  await nextTick()
  scrollToBottom()

  // 创建占位的AI消息（初始内容为空，流式填充）
  const aiMsgId = Date.now() + 1
  const aiMsg = {
    id: aiMsgId,
    session_id: currentSessionId.value,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
  }
  messages.value.push(aiMsg)

  try {
    // 使用 fetch + ReadableStream 读取 SSE 流
    const response = await fetch(`${API_BASE}/api/chat/sessions/${currentSessionId.value}/messages`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => null)
      throw new Error(errData?.detail || `请求失败 (${response.status})`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // 按行解析 SSE 事件
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留未完成的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (!dataStr) continue

          try {
            const event = JSON.parse(dataStr)

            if (event.type === 'token') {
              // 追加 token 到 AI 消息
              aiMsg.content += event.content
              // 触发响应式更新（直接修改引用的内容）
              messages.value = [...messages.value]
              scrollToBottom()
            } else if (event.type === 'done') {
              // 流式完成
              if (event.title) {
                // 更新会话标题
                const session = sessions.value.find(s => s.id === currentSessionId.value)
                if (session) {
                  session.title = event.title
                  session.updated_at = new Date().toISOString()
                }
              }
            } else if (event.type === 'error') {
              // AI回复出错，显示错误信息
              if (!aiMsg.content) {
                aiMsg.content = event.content
                messages.value = [...messages.value]
              }
            }
          } catch {
            // 忽略解析错误的行
          }
        }
      }
    }
  } catch (e: any) {
    // 如果完全没有收到任何回复，显示错误
    if (!aiMsg.content) {
      aiMsg.content = '抱歉，网络连接失败，请检查后端是否启动。'
      messages.value = [...messages.value]
    }
    console.error('流式请求失败:', e)
  } finally {
    isLoading.value = false
    // 兜底：再次确保输入框被清空
    inputMessage.value = ''
    const ta2 = document.querySelector('.chat-input textarea') as HTMLTextAreaElement | null
    if (ta2 && ta2.value !== '') {
      ta2.value = ''
      ta2.dispatchEvent(new Event('input', { bubbles: true }))
    }
    // 更新会话时间
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session) {
      session.updated_at = new Date().toISOString()
    }
    await nextTick()
    scrollToBottom()
    focusInput()
  }
}

/** 快捷提问 */
function quickQuestion(q: string) {
  if (!isLoggedIn.value) {
    message.warning('请先登录')
    router.push('/login')
    return
  }

  if (!currentSessionId.value) {
    // 自动创建新会话
    createNewSession().then(() => {
      nextTick(() => {
        // 等待会话创建完成并切换后，再发送消息
        setTimeout(() => {
          inputMessage.value = q
          sendMessage()
        }, 300)
      })
    })
    return
  }

  inputMessage.value = q
  sendMessage()
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

/** 滚动事件 */
function handleScroll() {
  // 可用于懒加载更多历史消息（未来扩展）
}

/** 聚焦输入框 */
function focusInput() {
  nextTick(() => {
    try {
      const textarea = document.querySelector('.chat-input textarea') as HTMLTextAreaElement
      if (textarea) textarea.focus()
    } catch {}
  })
}

/** 监听当前会话ID变化 */
watch(currentSessionId, (newId) => {
  if (newId) {
    // 重新获取消息
    fetchMessages(newId)
  }
})

onMounted(() => {
  checkAuth()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 134px); /* header + footer + padding */
  background: #f5f7fa;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  max-width: 1400px;
  margin: 0 auto;
}

/* ============ 侧边栏 ============ */
.chat-sidebar {
  width: 280px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
  flex-shrink: 0;
}

.chat-sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar-icon {
  font-size: 24px;
}

.new-chat-btn {
  width: 100%;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  height: 40px;
  font-size: 14px;
}

.chat-sidebar.collapsed .new-chat-btn {
  width: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}

/* 会话列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-list::-webkit-scrollbar {
  width: 4px;
}

.session-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  gap: 8px;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.session-item.active {
  background: rgba(102, 126, 234, 0.3);
  border: 1px solid rgba(102, 126, 234, 0.5);
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.session-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.session-actions {
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.session-icon-collapsed {
  font-size: 20px;
  margin: 0 auto;
}

/* 折叠按钮 */
.sidebar-collapse-btn {
  padding: 12px;
  text-align: center;
  cursor: pointer;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  transition: color 0.2s;
  flex-shrink: 0;
}

.sidebar-collapse-btn:hover {
  color: white;
}

/* ============ 主聊天区域 ============ */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  min-width: 0;
}

/* 消息容器 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #d0d5dd;
  border-radius: 3px;
}

/* 欢迎区域 */
.welcome-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px;
}

.welcome-icon {
  font-size: 80px;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}

.welcome-desc {
  font-size: 16px;
  color: #666;
  margin-bottom: 32px;
}

.welcome-suggestions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-width: 500px;
  width: 100%;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: white;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.suggestion-item:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
}

.suggestion-icon {
  font-size: 24px;
}

/* 消息项 */
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: #f0f0f0;
  flex-shrink: 0;
}

.message-item.user .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-item.user .message-content {
  align-items: flex-end;
}

.message-bubble {
  padding: 14px 18px;
  border-radius: 18px;
  line-height: 1.6;
  font-size: 15px;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-item.assistant .message-bubble {
  background: white;
  border: 1px solid #e8e8e8;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #333;
}

.message-item.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-top-right-radius: 4px;
}

.message-time {
  font-size: 11px;
  color: #999;
  padding: 0 8px;
}

/* 思考中动画 */
.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 80px;
}

.thinking-dots {
  display: flex;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: thinking 1.4s infinite ease-in-out;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}
.dot:nth-child(2) {
  animation-delay: -0.16s;
}
.dot:nth-child(3) {
  animation-delay: 0s;
}

@keyframes thinking {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.3;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.thinking-text {
  font-size: 14px;
  color: #999;
}

/* 输入区域 */
.input-area {
  padding: 16px 24px;
  border-top: 1px solid #e8e8e8;
  background: white;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  border-radius: 12px;
  border: 2px solid #e8e8e8;
  transition: all 0.3s ease;
  font-size: 15px;
  padding: 10px 16px;
  resize: none;
}

.chat-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.send-btn {
  height: 44px;
  width: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.send-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.input-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #bbb;
  text-align: center;
}

.login-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px;
}

.login-tip .ant-btn {
  border-radius: 8px;
  height: 48px;
  font-size: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-container {
    height: calc(100vh - 100px);
    border-radius: 0;
  }

  .chat-sidebar {
    width: 60px;
  }

  .chat-sidebar.collapsed {
    width: 0;
    overflow: hidden;
  }

  .message-content {
    max-width: 85%;
  }

  .welcome-suggestions {
    grid-template-columns: 1fr;
  }
}
</style>
