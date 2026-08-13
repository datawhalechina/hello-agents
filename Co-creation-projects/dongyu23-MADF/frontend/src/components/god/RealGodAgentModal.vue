<template>
  <a-modal
    v-model:open="visible"
    title="上帝模式：创造真实智能体 (联网版)"
    width="1000px"
    :footer="null"
    @cancel="handleCancel"
    class="god-agent-modal"
    :bodyStyle="{ padding: 0, height: '80vh' }"
    centered
  >
    <div class="god-agent-container">
      <div class="chat-window" ref="chatWindowRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
          <div class="avatar">
            <a-avatar v-if="msg.role === 'assistant'" style="background-color: #faad14">R</a-avatar>
            <a-avatar v-else style="background-color: #1890ff">U</a-avatar>
          </div>
          <div class="content-wrapper">
            <!-- User Message -->
            <div v-if="msg.role === 'user'" class="bubble user-bubble">
              {{ msg.content }}
            </div>

            <!-- Assistant Message (Structured Items) -->
            <template v-else>
               <!-- Fallback for simple content -->
               <div v-if="msg.content && (!msg.items || msg.items.length === 0)" class="bubble">
                 {{ msg.content }}
               </div>

               <!-- Structured Items -->
               <div v-for="(item, i) in msg.items" :key="i" class="msg-item">
                 
                 <!-- 1. Normal Text -->
                 <div v-if="item.type === 'text'" class="bubble">
                   {{ item.content }}
                 </div>

                 <!-- 2. Search Intent (Thought) -->
                 <div v-else-if="item.type === 'thought'" class="bubble thought-bubble">
                   <div class="thought-header">
                     <span class="icon">🤔</span> 思考过程
                   </div>
                   <div class="thought-content">{{ item.content }}</div>
                 </div>

                 <!-- 3. Searching State -->
                 <div v-else-if="item.type === 'search'" class="search-block">
                   <div class="search-status">
                     <span v-if="item.status === 'loading'" class="icon loading">⏳</span>
                     <span v-else class="icon success">✅</span>
                     <span class="status-text">
                       {{ item.status === 'loading' ? '正在搜索' : '搜索完成' }}: 
                       <span class="query">{{ item.query }}</span>
                     </span>
                   </div>
                   <div v-if="item.status === 'done' && item.result" class="search-result">
                     <a-collapse ghost size="small">
                        <a-collapse-panel key="1" header="查看搜索结果">
                          <pre>{{ item.result }}</pre>
                        </a-collapse-panel>
                     </a-collapse>
                   </div>
                 </div>

                 <!-- 4. Generated Persona -->
                 <div v-else-if="item.type === 'persona'" class="persona-block">
                   <a-card 
                    size="small" 
                    class="persona-card"
                    :title="item.persona.name"
                   >
                     <template #extra>
                        <a-tag color="orange">{{ item.persona.title }}</a-tag>
                     </template>
                     <p class="persona-bio">{{ item.persona.bio }}</p>
                     <div class="persona-tags">
                        <a-tag v-for="t in (item.persona.theories || []).slice(0, 3)" :key="t">{{ t }}</a-tag>
                     </div>
                     <div class="actions">
                        <a-button type="primary" size="small" @click="handleViewPersona">查看详情</a-button>
                     </div>
                   </a-card>
                 </div>

                 <!-- 6. Status/Progress -->
                 <div v-else-if="item.type === 'status'" class="status-block">
                   <div class="status-content">
                     <span class="icon">🚀</span> 
                     <span class="status-text">{{ item.content }}</span>
                   </div>
                 </div>

                 <!-- 5. Error -->
                 <div v-else-if="item.type === 'error'" class="bubble error-bubble">
                   ❌ {{ item.content }}
                 </div>
               </div>
            </template>
          </div>
        </div>
        
        <div v-if="loading && (!messages[messages.length-1]?.items || messages[messages.length-1]?.items?.length === 0)" class="message-item assistant">
          <div class="avatar">
            <a-avatar style="background-color: #faad14">R</a-avatar>
          </div>
          <div class="content-wrapper">
            <div class="bubble loading">
              <a-spin size="small" /> 正在呼唤上帝...
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-textarea
          v-model:value="input"
          placeholder="描述您想要创建的真实人物... (Enter 发送, Shift+Enter 换行)"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="loading"
          class="custom-textarea"
        />
        <a-button type="primary" class="send-btn" @click="handleSend" :loading="loading">
          <template #icon><send-outlined /></template>
          发送
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePersonaStore } from '@/stores/persona'
import { SendOutlined } from '@ant-design/icons-vue'

interface MessageItem {
  type: 'text' | 'thought' | 'search' | 'persona' | 'error' | 'status'
  content?: string
  query?: string
  result?: string
  status?: 'loading' | 'done'
  persona?: any
  current?: number
  total?: number
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content?: string // For user messages or simple assistant messages
  items?: MessageItem[] // For structured assistant messages
  timestamp: number
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open'])

const router = useRouter()
const personaStore = usePersonaStore()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMessage[]>([])
const loading = ref(false)
const totalToGenerate = ref(1)

const visible = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindowRef.value) {
      chatWindowRef.value.scrollTop = chatWindowRef.value.scrollHeight
    }
  })
}

watch(() => props.open, (val) => {
  if (val) {
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '',
        items: [{ type: 'text', content: '我是联网版上帝智能体。我可以搜索互联网信息，为您创造基于真实背景的深度角色。' }],
        timestamp: Date.now()
      })
    }
    scrollToBottom()
  }
})

watch(() => messages.value.length, scrollToBottom)
// Deep watch for items updates
watch(() => messages.value[messages.value.length - 1]?.items, scrollToBottom, { deep: true })

const handleSend = async () => {
  if (!input.value.trim() || loading.value) return
  
  const prompt = input.value
  input.value = ''
  
  // Add user message
  messages.value.push({
    role: 'user',
    content: prompt,
    timestamp: Date.now()
  })
  
  loading.value = true
  totalToGenerate.value = 1 // Reset
  
  // Prepare assistant message container
  const assistantMsg = ref<ChatMessage>({
    role: 'assistant',
    items: [],
    timestamp: Date.now()
  })
  messages.value.push(assistantMsg.value)
  
  try {
    // Fetch SSE
    const response = await fetch('/api/v1/god/generate_real', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ prompt, n: 1 })
    })

    if (!response.ok) {
        let detail = `角色生成服务请求失败（HTTP ${response.status}）`
        try {
          const payload = await response.json()
          if (typeof payload?.detail === 'string' && payload.detail.trim()) {
            detail = payload.detail
          }
        } catch {
          // Keep the status-based message when the response is not JSON.
        }
        throw new Error(detail)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) throw new Error('No reader')

    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      
      for (const line of parts) {
        if (line.trim().startsWith('data: ')) {
          try {
            const jsonStr = line.trim().slice(6)
            if (!jsonStr) continue
            
            const event = JSON.parse(jsonStr)
            const items = assistantMsg.value.items || []
            
            if (event.type === 'count') {
                totalToGenerate.value = event.content
                
            } else if (event.type === 'thought_start') {
                // High level status update
                items.push({ type: 'status', content: event.content })
                
            } else if (event.type === 'progress') {
                // Update total and find the last status item to update
                if (event.total) totalToGenerate.value = event.total
                
                // Find last status item
                const lastStatus = [...items].reverse().find(i => i.type === 'status')
                if (lastStatus) {
                    lastStatus.content = `=== 开始生成第 ${event.current} 位角色 (共 ${event.total} 位) ===`
                }
                
            } else if (event.type === 'thought_chunk') {
                // Find active thought item or create one
                let lastItem = items[items.length - 1]
                
                // Skip creating thought item if the last item is status (which happens at start)
                // But we need to put thoughts SOMEWHERE.
                // If last item is status, create a thought item.
                if (!lastItem || lastItem.type !== 'thought') {
                    lastItem = { type: 'thought', content: '' }
                    items.push(lastItem)
                }
                lastItem.content += event.content
                
            } else if (event.type === 'thought') {
                // Finalized thought (cleaned up)
                // Update the last thought item if exists
                let lastItem = items[items.length - 1]
                if (lastItem && lastItem.type === 'thought') {
                    lastItem.content = event.content
                } else {
                    items.push({ type: 'thought', content: event.content })
                }
                
            } else if (event.type === 'action') {
                // e.g. "搜索: keyword"
                const content = event.content
                if (content.includes('搜索') || content.includes('Search')) {
                    // Extract query roughly
                    const query = content.replace(/搜索[:：]|Search\[|\]/g, '').trim()
                    items.push({ type: 'search', query: query, status: 'loading', result: '' })
                } else {
                    // Other actions (like Finish) - maybe log as text?
                    // Usually Finish is handled by result event, but the Action: Finish log exists.
                    // We can ignore Finish action log or show as text.
                    // Let's show as debug/text if not search
                    // items.push({ type: 'text', content: `[Action] ${content}` })
                }
                
            } else if (event.type === 'observation') {
                // Update last search item
                // Find the last search item that is loading
                // Reverse search
                let searchItem = [...items].reverse().find(i => i.type === 'search' && i.status === 'loading')
                if (searchItem) {
                    searchItem.status = 'done'
                    // Fix: Clean up observation content if it contains raw JSON string artifacts
                    let cleanContent = event.content;
                    // Check if content looks like a JSON string dump (starts with " and ends with ")
                    // and try to parse it if it's double encoded
                    if (typeof cleanContent === 'string') {
                        // Remove potential surrounding quotes and unescape
                        // But simple approach: just display it. Pre tag handles formatting.
                        // If user complains about specific artifacts like "[ \n " \n \", handle them:
                        if (cleanContent.startsWith('[\n "') || cleanContent.startsWith('["')) {
                             try {
                                 const parsed = JSON.parse(cleanContent);
                                 if (Array.isArray(parsed)) {
                                     cleanContent = parsed.join('\n');
                                 }
                             } catch (e) {
                                 // ignore
                             }
                        }
                    }
                    searchItem.result = cleanContent
                } else {
                    // Fallback
                    items.push({ type: 'text', content: `[Observation] ${event.content}` })
                }
                
            } else if (event.type === 'result') {
                // Persona(s) generated
                const results = Array.isArray(event.content) ? event.content : [event.content]
                for (const p of results) {
                    items.push({ type: 'persona', persona: p })
                }
                items.push({ type: 'text', content: `✅ 生成完成！` })
                
            } else if (event.type === 'error') {
                items.push({ type: 'error', content: event.content })
                message.error(event.content || '生成过程中发生错误')
            }
            
            scrollToBottom()
          } catch (e) {
            console.error('JSON parse error', e)
          }
        }
      }
    }

  } catch (error: any) {
    const errorMessage = error instanceof Error && error.message
      ? error.message
      : '角色生成请求失败，请稍后重试'
    assistantMsg.value.items?.push({ type: 'error', content: errorMessage })
    message.error(errorMessage)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}

const handleViewPersona = () => {
  visible.value = false
  personaStore.fetchPersonas()
  router.push('/personas')
}

// Watch visibility to refresh list when modal closes if generation happened
watch(visible, (newVal) => {
  if (!newVal && messages.value.some(m => m.items?.some(i => i.type === 'persona'))) {
    personaStore.fetchPersonas()
  }
})
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-radius: 0;
}

.chat-window {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7f9;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 95%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.assistant {
  align-self: flex-start;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  /* Ensure bubbles don't stretch too wide if content is short */
  align-items: flex-start; 
}

.message-item.user .content-wrapper {
  align-items: flex-end;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px 12px 12px 0;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-width: 100%;
}

.user-bubble {
  background: #1890ff;
  color: #fff;
  border-radius: 12px 12px 0 12px;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.2);
}

.thought-bubble {
  background: #fafafa;
  border: 1px solid #ebebeb;
  border-left: 4px solid #faad14;
  color: #555;
  font-size: 13px;
  width: 100%;
  border-radius: 8px;
}

.thought-header {
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.search-block {
  background: #f0faff;
  border: 1px solid #bae7ff;
  border-radius: 8px;
  padding: 10px 14px;
  width: 100%;
  font-size: 13px;
}

.search-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-text {
  flex: 1;
}

.query {
  font-weight: 500;
  color: #1890ff;
}

.search-result {
  margin-top: 8px;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}

.persona-block {
  width: 100%;
}

.error-bubble {
  background: #fff1f0;
  border: 1px solid #ffa39e;
  color: #cf1322;
}

.status-block {
  width: 100%;
  margin: 8px 0;
  text-align: center;
}

.status-content {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #52c41a;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.loading {
  font-style: italic;
  color: #8c8c8c;
}

.persona-card {
  width: 100%;
  margin-bottom: 8px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  border: 1px solid #f0f0f0;
}

.persona-card :deep(.ant-card-head) {
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.persona-bio {
  font-size: 12px;
  color: #666;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.persona-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.input-area {
  padding: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  border-top: 1px solid #f0f0f0;
  margin-top: 0;
  background: #fff;
  flex-shrink: 0;
}

.custom-textarea {
  border-radius: 8px;
  resize: none;
  padding: 8px 12px;
  transition: all 0.3s;
}

.custom-textarea:hover, .custom-textarea:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

.send-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
