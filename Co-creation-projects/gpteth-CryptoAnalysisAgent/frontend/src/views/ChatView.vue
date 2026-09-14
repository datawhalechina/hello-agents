<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, streamChat } from '../api'
import { renderMarkdown } from '../markdown'

const STORAGE_KEY = 'caa.lastSessionId'
const route = useRoute()
const router = useRouter()
const input = ref('')
const loading = ref(false)
const sessionId = ref(null)
const messages = ref([])
const scroller = ref(null)
const abort = ref(null)

const SUGGESTIONS = [
  '帮我分析 BTC 当前走势',
  '记住我偏稳健，主要看 BTC 和 ETH',
  '对比一下 SOL 和 ETH 的风险',
]

function useSuggestion(text) {
  input.value = text
  send()
}

function pushUser(text) {
  messages.value.push({ role: 'user', content: text })
}

function startAssistant() {
  messages.value.push({ role: 'assistant', thought: '', tools: [], content: '' })
  return messages.value[messages.value.length - 1]
}

async function scroll() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function loadHistory(id) {
  const data = await api(`/session/${id}/history`)
  messages.value = (data.messages || [])
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({
      role: m.role,
      content: m.content || '',
      tools: m.metadata?.tools || [],
      thought: '',
    }))
  await scroll()
}

async function ensureSession() {
  const fromUrl = route.query.session
  const last = localStorage.getItem(STORAGE_KEY)
  const id = fromUrl || last
  if (id) {
    sessionId.value = id
    localStorage.setItem(STORAGE_KEY, id)
    if (!fromUrl) router.replace({ query: { session: id } })
    try {
      await loadHistory(id)
    } catch {
      messages.value = []
    }
    return
  }
  const created = await api('/session/create', { method: 'POST', body: '{}' })
  sessionId.value = created.session_id
  localStorage.setItem(STORAGE_KEY, created.session_id)
  router.replace({ query: { session: created.session_id } })
}

async function newChat() {
  const created = await api('/session/create', { method: 'POST', body: '{}' })
  sessionId.value = created.session_id
  localStorage.setItem(STORAGE_KEY, created.session_id)
  messages.value = []
  router.replace({ query: { session: created.session_id } })
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  pushUser(text)
  const assistant = startAssistant()
  loading.value = true
  abort.value = new AbortController()
  await scroll()
  try {
    await streamChat(text, sessionId.value, (event) => {
      if (event.type === 'session' && event.session_id) {
        sessionId.value = event.session_id
        localStorage.setItem(STORAGE_KEY, event.session_id)
        router.replace({ query: { session: event.session_id } })
      } else if (event.type === 'thought') {
        assistant.thought = (assistant.thought || '') + (event.content || '')
      } else if (event.type === 'tool_start') {
        assistant.tools.push({ tool: event.tool, args: event.args, result: '', status: 'running' })
      } else if (event.type === 'tool_finish') {
        const last = [...assistant.tools].reverse().find((t) => t.tool === event.tool && t.status === 'running')
        if (last) {
          last.result = event.result || ''
          last.status = 'done'
        }
      } else if (event.type === 'chunk') {
        assistant.content += event.content || ''
      } else if (event.type === 'error') {
        assistant.content = assistant.content || `错误: ${event.error}`
      }
      scroll()
    }, abort.value.signal)
  } catch (err) {
    if (err.name !== 'AbortError') {
      assistant.content = assistant.content || err.message
    }
  } finally {
    loading.value = false
    abort.value = null
    await scroll()
  }
}

function stop() {
  abort.value?.abort()
}

onMounted(ensureSession)
</script>

<template>
  <div class="page chat-page">
    <header class="page-head chat-head">
      <div>
        <h2>智能对话</h2>
        <p>ReAct 推理 · 工具调用 · 记忆会写入今日日记</p>
      </div>
      <button class="ghost" @click="newChat">新会话</button>
    </header>

    <div class="panel transcript" ref="scroller">
      <div v-if="!messages.length" class="empty">
        <p>发送消息开始对话。需要行情时我会调用多维分析工具。</p>
        <div class="chips">
          <button v-for="item in SUGGESTIONS" :key="item" type="button" class="ghost" @click="useSuggestion(item)">
            {{ item }}
          </button>
        </div>
      </div>
      <article v-for="(msg, index) in messages" :key="index" :class="['bubble', msg.role]">
        <span class="who">{{ msg.role === 'user' ? '你' : '助手' }}</span>
        <div v-if="msg.thought" class="thought">Thought: {{ msg.thought }}</div>
        <div v-for="(tool, tIndex) in msg.tools || []" :key="tIndex" class="tool" :class="tool.status">
          <button type="button" class="tool-head" @click="tool.open = !tool.open">
            <strong>{{ tool.status === 'running' ? '调用中' : '已完成' }} · {{ tool.tool }}</strong>
            <span>{{ tool.open ? '收起' : '展开' }}</span>
          </button>
          <div v-if="tool.open !== false && tool.status !== 'running'">
            <pre v-if="tool.args">{{ JSON.stringify(tool.args, null, 2) }}</pre>
            <pre v-if="tool.result">{{ tool.result }}</pre>
          </div>
        </div>
        <div v-if="loading && index === messages.length - 1 && msg.role === 'assistant' && !msg.content" class="dots">
          <span /><span /><span />
        </div>
        <div v-if="msg.content" class="md" v-html="renderMarkdown(msg.content)" />
      </article>
    </div>

    <form class="composer" @submit.prevent="send">
      <textarea
        v-model="input"
        rows="2"
        placeholder="输入问题，Shift+Enter 换行"
        @keydown.enter.exact.prevent="send"
      />
      <button v-if="loading" type="button" class="ghost" @click="stop">停止</button>
      <button v-else class="primary" type="submit" :disabled="!input.trim()">发送</button>
    </form>
  </div>
</template>

<style scoped>
.chat-page { gap: 14px; }
.chat-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0; }
.transcript {
  flex: 1;
  overflow: auto;
  padding: 18px;
}
.bubble { margin-bottom: 18px; }
.bubble.user { padding-left: 12px; border-left: 3px solid var(--accent); }
.who { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
.thought {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 8px;
  white-space: pre-wrap;
}
.tool {
  background: rgba(0,0,0,0.28);
  border-radius: 12px;
  padding: 10px 12px;
  margin: 8px 0;
  font-size: 13px;
}
.tool pre {
  white-space: pre-wrap;
  margin: 8px 0 0;
  color: var(--muted);
}
.composer {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.composer textarea {
  flex: 1;
  resize: none;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 14px;
  outline: none;
}
.chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
.tool-head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  background: none;
  border: 0;
  padding: 0;
  color: inherit;
}
.tool.running { border: 1px solid rgba(62, 224, 178, 0.35); }
.dots { display: flex; gap: 6px; padding: 8px 0; }
.dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}
.dots span:nth-child(2) { animation-delay: .15s; }
.dots span:nth-child(3) { animation-delay: .3s; }
@keyframes pulse {
  0%, 100% { opacity: .35; transform: scale(.85); }
  50% { opacity: 1; transform: scale(1); }
}
</style>
