import { type Ref } from 'vue'
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
  onConversationDirty?: (id: string, snapshot: SearchAgentMessage[]) => void
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
    const conversationId = ensureCurrentConversationId()
    const conversationMessages = messages.value
    userInput.value = ''
    isLoading.value = true
    conversationMessages.push({
      role: 'user',
      content: input,
      timestamp: Date.now(),
    })
    hasSearched.value = true
    const pIdx = conversationMessages.push({
      role: 'assistant', content: '正在搜索文献…', timestamp: Date.now(),
      toolCalls: [], results: [], total: 0, isError: false,
    }) - 1
    const msg = conversationMessages[pIdx]
    const persist = () => onConversationDirty?.(conversationId, conversationMessages)
    persist()
    scrollToBottom()
    try {
      const req = {
        message: input,
        history: conversationMessages.slice(0, -2).map((m) => ({ role: m.role, content: m.content })),
      }
      const applyStreamEvent = (ev: SearchAgentStreamEvent) => {
        if (ev.type === 'status' && ev.message) {
          msg.content = ev.message
          msg.isError = false
          persist()
        }
        if (ev.type === 'error' && ev.message) {
          msg.content = `抱歉，搜索出现了问题：${ev.message}`
          msg.isError = true
          msg.results = undefined
          msg.total = 0
          persist()
        }
      }
      const data = await searchAgentChatStream(req, applyStreamEvent)
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
      msg.content = `抱歉，出现了错误：${errText}`
      msg.timestamp = Date.now()
      msg.isError = true
      msg.results = undefined
      msg.total = 0
    } finally {
      isLoading.value = false
      persist()
      if (messages.value === conversationMessages) scrollToBottom()
    }
  }
  return { sendMessage }
}
