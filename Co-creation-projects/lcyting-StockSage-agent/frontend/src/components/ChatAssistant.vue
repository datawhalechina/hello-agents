<template>
  <div class="chat-assistant">
    <div class="chat-messages" ref="msgContainer">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['msg-item', msg.role]"
      >
        <div class="msg-avatar">{{ msg.role === 'user' ? 'U' : 'AI' }}</div>
        <div class="msg-content">
          <div class="msg-text" v-html="renderContent(msg.content)"></div>
        </div>
      </div>

      <div v-if="isStreaming" class="msg-item assistant">
        <div class="msg-avatar">AI</div>
        <div class="msg-content">
          <div v-if="currentThinking" class="msg-thinking">
            <el-icon class="is-loading"><Loading /></el-icon> {{ currentThinking }}
          </div>
          <div class="msg-text streaming-text" v-html="renderContent(streamingContent)"></div>
          <div v-if="currentEmotion" class="msg-emotion">{{ currentEmotion }}</div>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <el-input
        v-model="inputText"
        placeholder="输入您的问题..."
        @keyup.enter.exact="sendMessage"
        :disabled="isStreaming"
        clearable
      >
        <template #append>
          <el-button
            type="primary"
            @click="sendMessage"
            :loading="isStreaming"
            :disabled="!inputText.trim()"
          >
            发送
          </el-button>
        </template>
      </el-input>
    </div>

    <div class="chat-actions">
      <el-button size="small" @click="clearChat">清空对话</el-button>
      <el-button size="small" @click="historyVisible = true">
        <el-icon><Clock /></el-icon> 历史记录
      </el-button>
    </div>

    <HistoryDrawer
      v-model:visible="historyVisible"
      type="chat"
    />
  </div>
</template>

<script>
export default { name: 'ChatAssistant' }
</script>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import HistoryDrawer from './HistoryDrawer.vue'

const props = defineProps({
  stockCode: { type: String, default: '' },
  stockName: { type: String, default: '' },
  /** 当前是否在「AI对话助手」标签页（用于首次进入时展示问候语） */
  chatVisible: { type: Boolean, default: false },
})

const inputText = ref('')
const messages = ref([])
const isStreaming = ref(false)
const streamingContent = ref('')
const currentThinking = ref('')
const currentEmotion = ref('')
const msgContainer = ref(null)
const historyVisible = ref(false)

function buildGreetingText() {
  const name = (props.stockName || '').trim()
  const code = (props.stockCode || '').trim()
  const ctx =
    name && code
      ? `当前正在查看 **${name}（${code}）**。`
      : code
        ? `当前股票代码 **${code}**。`
        : ''
  return (
    `您好！我是 AI 对话助手。${ctx ? ctx + ' ' : ''}` +
    '我可以帮您分析舆情与财务数据、提供投资参考与风险提示、解答股票相关问题。\n\n' +
    '请直接在下方输入您的问题，例如：**分析该股的投资价值与主要风险**。'
  )
}

function seedGreeting() {
  if (messages.value.length > 0) return
  messages.value.push({ role: 'assistant', content: buildGreetingText() })
  scrollToBottom()
}

watch(
  () => props.chatVisible,
  (visible) => {
    if (visible) seedGreeting()
  }
)

onMounted(() => {
  if (props.chatVisible) seedGreeting()
})

function renderContent(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  isStreaming.value = true
  streamingContent.value = ''
  currentThinking.value = ''
  currentEmotion.value = ''
  scrollToBottom()

  try {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        stock_code: props.stockCode,
        stock_name: props.stockName,
        history: messages.value.slice(0, -1),
      }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const event = JSON.parse(line)
          handleChatEvent(event)
        } catch {
          // skip
        }
      }
    }

    const tail = buffer.trim()
    if (tail) {
      try {
        const event = JSON.parse(tail)
        handleChatEvent(event)
      } catch {
        /* ignore incomplete tail */
      }
    }

    const assistantText = (streamingContent.value || '').trim()
    if (assistantText) {
      messages.value.push({ role: 'assistant', content: assistantText })
    }
  } catch (e) {
    ElMessage.error('对话失败: ' + (e.message || '未知错误'))
  } finally {
    isStreaming.value = false
    streamingContent.value = ''
    currentThinking.value = ''
    currentEmotion.value = ''
  }
}

function handleChatEvent(event) {
  switch (event.type) {
    case 'thinking':
      currentThinking.value = event.content
      break
    case 'emotional':
      currentEmotion.value = event.content
      break
    case 'status':
      currentThinking.value = event.content
      break
    case 'delta':
      streamingContent.value += event.content || event.text || ''
      break
    case 'summary':
      streamingContent.value += '\n\n**总结**：' + (event.content || '') + '\n'
      break
    case 'done':
      currentThinking.value = ''
      break
    case 'error':
      streamingContent.value += '\n\n' + (event.content || event.message || '发生错误')
      break
  }
  scrollToBottom()
}

function clearChat() {
  messages.value = []
  streamingContent.value = ''
  seedGreeting()
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-assistant {
  display: flex;
  flex-direction: column;
  height: 500px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
}

.msg-item {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.msg-item.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.msg-item.user .msg-avatar { background: #409eff; color: white; }
.msg-item.assistant .msg-avatar { background: #67c23a; color: white; }

.msg-content {
  max-width: 75%;
}

.msg-item.user .msg-content { text-align: right; }

.msg-text {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.msg-item.user .msg-text { background: #409eff; color: white; }
.msg-item.assistant .msg-text { background: white; border: 1px solid #ebeef5; }

.msg-thinking {
  font-size: 12px;
  color: #e6a23c;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.msg-emotion {
  font-size: 12px;
  color: #67c23a;
  margin-top: 4px;
  padding: 4px 8px;
  background: #f0f9eb;
  border-radius: 4px;
}

.streaming-text {
  background: #ecf5ff !important;
}

.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: white;
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 16px;
  background: #fafafa;
  border-top: 1px solid #ebeef5;
}
</style>
