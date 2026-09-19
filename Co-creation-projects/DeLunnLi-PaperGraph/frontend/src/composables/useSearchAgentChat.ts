import { nextTick, type Ref } from 'vue'
import { searchAgentChatStream, type SearchAgentStreamEvent } from '@/services/api'
type ToolCall = {
  name: string
  status: 'running' | 'success' | 'error'
  params?: Record<string, any>
  result_summary?: string
}
type SearchAgentMessage = {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  searchParams?: any
  toolCalls?: ToolCall[]
  results?: any[]
  total?: number
  isError?: boolean
}
interface UseSearchAgentChatOptions {
  messages: Ref<SearchAgentMessage[]>
  userInput: Ref<string>
  isLoading: Ref<boolean>
  hasSearched: Ref<boolean>
  ensureCurrentConversationId: () => string
  scrollToBottom: () => void
  onConversationDirty?: () => void
}
export function useSearchAgentChat({
  messages,
  userInput,
  isLoading,
  hasSearched,
  ensureCurrentConversationId,
  scrollToBottom,
  onConversationDirty,
}: UseSearchAgentChatOptions) {
  const sendMessage = async () => {
    const input = userInput.value.trim()
    if (!input || isLoading.value) return
    ensureCurrentConversationId()
    userInput.value = ''
    await nextTick()
    messages.value.push({
      role: 'user',
      content: input,
      timestamp: Date.now(),
    })
    onConversationDirty?.()
    hasSearched.value = true
    await nextTick()
    userInput.value = ''
    isLoading.value = true
    const pIdx = messages.value.push({
      role: 'assistant', content: '正在搜索文献…', timestamp: Date.now(),
      toolCalls: [], results: [], total: 0, isError: false,
    }) - 1
    scrollToBottom()
    try {
      const req = {
        message: input,
        history: messages.value.slice(0, -2).map((m) => ({ role: m.role, content: m.content })),
      }
      const applyStreamEvent = (ev: SearchAgentStreamEvent) => {
        const msg = messages.value[pIdx]
        if (!msg) return
        if (ev.type === 'status' && ev.message) {
          msg.content = ev.message
          msg.isError = false
          return
        }
        if (ev.type === 'error' && ev.message) {
          msg.content = `抱歉，搜索出现了问题：${ev.message}`
          msg.isError = true
          msg.results = undefined
          msg.total = 0
        }
      }
      const data = await searchAgentChatStream(req, applyStreamEvent)
      const msg = messages.value[pIdx]
      if (!msg) return
      if (data.success) {
        msg.content = data.response
        msg.searchParams = data.search_params
        msg.toolCalls = data.tool_calls
        msg.results = data.papers
        msg.total = data.total || data.papers?.length || 0
        msg.isError = false
        msg.timestamp = Date.now()
      } else {
        msg.content = `抱歉，搜索出现了问题：${data.message || '未知错误'}`
        msg.timestamp = Date.now()
        msg.isError = true
        msg.results = undefined
        msg.total = 0
      }
    } catch (error: any) {
      const errText = String(error?.message || '请稍后重试')
      if (messages.value[pIdx]) {
        const msg = messages.value[pIdx]
        msg.content = `抱歉，出现了错误：${errText}`
        msg.timestamp = Date.now()
        msg.isError = true
        msg.results = undefined
        msg.total = 0
      } else {
        messages.value.push({
          role: 'assistant',
          content: `抱歉，出现了错误：${errText}`,
          timestamp: Date.now(),
          isError: true,
          results: undefined,
          total: 0,
        })
      }
    } finally {
      userInput.value = ''
      isLoading.value = false
      onConversationDirty?.()
      scrollToBottom()
    }
  }
  return { sendMessage }
}