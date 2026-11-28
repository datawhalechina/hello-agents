<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const router = useRouter()
const STORAGE_KEY = 'wellness-chat-v1'
const WELCOME = {
  role: 'assistant',
  content: '你好，我是 Wellness Assistant。可以用自然语言记录体重、睡眠，生成减脂或康复运动计划，也可以根据身体反馈调整计划。',
}

function createSessionId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : String(Date.now())
}

function readSavedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && parsed.sessionId && Array.isArray(parsed.messages)) return parsed
  } catch (error) {
    console.warn('读取本地聊天记录失败', error)
  }
  return null
}

const saved = readSavedState()
const sessionId = ref(saved?.sessionId || createSessionId())
const messages = ref(saved?.messages?.length ? saved.messages : [WELCOME])
const input = ref(saved?.draft || '')
const loading = ref(false)
const restored = ref(false)
const historyRef = ref(null)

const examples = [
  '帮我记录今天体重 68 公斤、睡眠 7 小时，并生成一份减脂运动计划',
  '训练后膝盖不适，请降低计划强度',
  '帮我复盘最近 7 天的健康数据',
]

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sessionId: sessionId.value,
        messages: messages.value,
        draft: input.value,
      }),
    )
  } catch (error) {
    console.warn('保存本地聊天记录失败', error)
  }
}

watch([messages, input], persist, { deep: true })

async function scrollToBottom() {
  await nextTick()
  if (historyRef.value) historyRef.value.scrollTop = historyRef.value.scrollHeight
}

async function restoreFromServer() {
  if (saved) return
  try {
    const history = await api.chatHistory()
    if (!history.messages?.length) return
    sessionId.value = history.session_id
    messages.value = [
      WELCOME,
      ...history.messages.map((item) => ({
        role: item.role,
        content: item.content,
        traceId: item.role === 'assistant' ? item.trace_id : undefined,
      })),
    ]
    restored.value = true
  } catch (error) {
    console.warn('从服务器恢复聊天记录失败', error)
  }
}

async function send(text) {
  const message = (text ?? input.value).trim()
  if (!message || loading.value) return
  messages.value.push({ role: 'user', content: message })
  input.value = ''
  loading.value = true
  await scrollToBottom()
  try {
    const data = await api.chat(message, sessionId.value)
    messages.value.push({ role: 'assistant', content: data.reply, traceId: data.trace_id })
  } catch (error) {
    ElMessage.error(error.message)
    messages.value.push({ role: 'assistant', content: `调用失败：${error.message}` })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function startNewChat() {
  if (loading.value) return
  sessionId.value = createSessionId()
  messages.value = [WELCOME]
  input.value = ''
  restored.value = false
  persist()
  ElMessage.success('已开启新对话')
}

function openTrace(id) {
  router.push({ name: 'trace', query: { id } })
}

onMounted(async () => {
  await restoreFromServer()
  persist()
  await scrollToBottom()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>健康对话</h2>
      <p>通过自然语言记录健康数据、生成与调整运动方案；切换标签或刷新页面会保留当前会话。</p>
    </div>

    <div class="disclaimer" style="margin-bottom: 16px">
      本项目仅作健康辅助用途，不具备医疗诊断能力，输出内容不能替代专业医师诊疗。
    </div>

    <div class="toolbar session-bar">
      <span class="muted">会话 {{ sessionId.slice(0, 8) }} · {{ messages.length }} 条消息</span>
      <div style="display: flex; gap: 10px; align-items: center">
        <el-tag v-if="restored" type="info" size="small">已从服务器恢复</el-tag>
        <el-button size="small" :disabled="loading" @click="startNewChat">开启新对话</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <div ref="historyRef" class="history">
        <div v-for="(item, index) in messages" :key="index" class="message-row" :class="item.role">
          <div class="bubble">
            <div class="role">{{ item.role === 'user' ? '我' : 'Wellness Agent' }}</div>
            <div class="content">{{ item.content }}</div>
            <el-button
              v-if="item.traceId"
              link
              type="primary"
              size="small"
              @click="openTrace(item.traceId)"
            >
              查看调用链路
            </el-button>
          </div>
        </div>
        <div v-if="loading" class="muted">Agent 正在思考并调用工具…</div>
      </div>

      <div class="composer">
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          placeholder="例如：帮我记录今天体重、睡眠情况，并生成一份减脂运动计划"
          :disabled="loading"
          @keydown.enter.exact.prevent="send()"
        />
        <el-button type="primary" :loading="loading" @click="send()">发送</el-button>
      </div>
      <div class="examples">
        <span class="muted">试试：</span>
        <el-tag
          v-for="example in examples"
          :key="example"
          class="example"
          @click="send(example)"
        >
          {{ example }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.history {
  height: 46vh;
  overflow-y: auto;
  padding: 8px 4px 16px;
}

.session-bar {
  justify-content: space-between;
}

.message-row {
  display: flex;
  margin-bottom: 14px;
}

.message-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 76%;
  background: #f3f4f6;
  border-radius: 10px;
  padding: 10px 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.message-row.user .bubble {
  background: #409eff;
  color: #ffffff;
}

.role {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 4px;
}

.composer {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.examples {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 14px;
}

.example {
  cursor: pointer;
}
</style>
