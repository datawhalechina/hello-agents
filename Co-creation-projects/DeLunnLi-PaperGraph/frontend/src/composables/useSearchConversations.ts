import { ref, type Ref } from 'vue'
interface SearchConversation<TMessage> {
  id: string
  title: string
  messages: TMessage[]
  timestamp: number
  messageCount: number
}
interface UseSearchConversationsOptions<TMessage> {
  messages: Ref<TMessage[]>
  hasSearched: Ref<boolean>
  userInput: Ref<string>
  titleFromMessages: (messages: TMessage[]) => string
  stateStorageKey?: string
  conversationsStorageKey?: string
}
export function useSearchConversations<TMessage>({
  messages,
  hasSearched,
  userInput,
  titleFromMessages,
  stateStorageKey = 'searchAgentState',
  conversationsStorageKey = 'searchAgentConversations',
}: UseSearchConversationsOptions<TMessage>) {
  const conversations = ref<SearchConversation<TMessage>[]>([])
  const currentConversationId = ref<string | null>(null)
  const PERSIST_DEBOUNCE_MS = 900
  let conversationsPersistTimer: ReturnType<typeof setTimeout> | null = null
  let statePersistTimer: ReturnType<typeof setTimeout> | null = null
  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).slice(2)
  }
  function flushConversationsPersist() {
    if (conversationsPersistTimer) {
      clearTimeout(conversationsPersistTimer)
      conversationsPersistTimer = null
    }
    try {
      localStorage.setItem(conversationsStorageKey, JSON.stringify(conversations.value))
    } catch (e) {
      console.error('Failed to save conversations:', e)
    }
  }
  function saveConversations(immediate = false) {
    if (immediate) {
      flushConversationsPersist()
      return
    }
    if (conversationsPersistTimer) clearTimeout(conversationsPersistTimer)
    conversationsPersistTimer = setTimeout(flushConversationsPersist, PERSIST_DEBOUNCE_MS)
  }
  function loadConversations() {
    try {
      const saved = localStorage.getItem(conversationsStorageKey)
      if (saved) conversations.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to load conversations:', e)
      conversations.value = []
    }
  }
  function flushStatePersist() {
    if (statePersistTimer) {
      clearTimeout(statePersistTimer)
      statePersistTimer = null
    }
    try {
      localStorage.setItem(
        stateStorageKey,
        JSON.stringify({
          messages: messages.value,
          hasSearched: hasSearched.value,
          currentConversationId: currentConversationId.value,
          timestamp: Date.now(),
        })
      )
    } catch {
    }
  }
  function saveState(immediate = false) {
    if (immediate) {
      flushStatePersist()
      return
    }
    if (statePersistTimer) clearTimeout(statePersistTimer)
    statePersistTimer = setTimeout(flushStatePersist, PERSIST_DEBOUNCE_MS)
  }
  function loadState() {
    try {
      const saved = localStorage.getItem(stateStorageKey)
      if (!saved) return
      const state = JSON.parse(saved) as {
        messages?: TMessage[]
        hasSearched?: boolean
        currentConversationId?: string | null
        timestamp?: number
      }
      if (!state.timestamp || Date.now() - state.timestamp >= 24 * 60 * 60 * 1000) return
      clearState()
    } catch (e) {
      console.error('Failed to load search state:', e)
    }
  }
  function clearState() {
    if (statePersistTimer) {
      clearTimeout(statePersistTimer)
      statePersistTimer = null
    }
    localStorage.removeItem(stateStorageKey)
  }
  function saveCurrentConversation() {
    if (!hasSearched.value || messages.value.length === 0) return
    const convId = currentConversationId.value || generateId()
    if (!currentConversationId.value) currentConversationId.value = convId
    const next: SearchConversation<TMessage> = {
      id: convId,
      title: titleFromMessages(messages.value),
      messages: JSON.parse(JSON.stringify(messages.value)),
      timestamp: Date.now(),
      messageCount: messages.value.length,
    }
    const existingIndex = conversations.value.findIndex((c) => c.id === convId)
    if (existingIndex >= 0) conversations.value.splice(existingIndex, 1, next)
    else conversations.value.unshift(next)
    saveConversations()
  }
  function ensureCurrentConversationId(): string {
    if (!currentConversationId.value) currentConversationId.value = generateId()
    return currentConversationId.value
  }
  function loadConversation(id: string) {
    const conversation = conversations.value.find((c) => c.id === id)
    if (!conversation) return
    saveCurrentConversation()
    messages.value = [...conversation.messages]
    hasSearched.value = true
    currentConversationId.value = id
    saveState()
  }
  function createNewConversation(saveCurrent = true) {
    if (saveCurrent && hasSearched.value && messages.value.length > 0) {
      if (!currentConversationId.value) currentConversationId.value = generateId()
      saveCurrentConversation()
    }
    messages.value = []
    hasSearched.value = false
    userInput.value = ''
    currentConversationId.value = null
    clearState()
  }
  function removeConversation(id: string) {
    const index = conversations.value.findIndex((c) => c.id === id)
    if (index < 0) return
    conversations.value.splice(index, 1)
    saveConversations()
    if (currentConversationId.value === id) createNewConversation(false)
  }
  function persistConversationAndState(immediate = false) {
    if (!hasSearched.value) return
    saveCurrentConversation()
    saveState(immediate)
    if (immediate) saveConversations(true)
  }
  function initFromStorage() {
    loadConversations()
    loadState()
  }
  function formatTime(timestamp: number): string {
    const date = new Date(timestamp)
    const now = new Date()
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
  return {
    conversations,
    currentConversationId,
    saveCurrentConversation,
    ensureCurrentConversationId,
    saveState,
    persistConversationAndState,
    loadConversation,
    createNewConversation,
    removeConversation,
    initFromStorage,
    formatTime,
  }
}