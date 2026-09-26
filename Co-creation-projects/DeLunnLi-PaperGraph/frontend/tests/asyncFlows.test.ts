import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
const api = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), getLibrary: vi.fn(), folders: vi.fn(), getPaper: vi.fn(), stream: vi.fn(),
}))
vi.mock('@/services/api/client', () => ({ apiClient: { get: api.get, post: api.post } }))
vi.mock('@/services/api', () => ({
  default: { get: api.get }, getLibrary: api.getLibrary, getLibraryCategoryFolders: api.folders,
  deletePaper: vi.fn(), getPaper: api.getPaper, searchAgentChatStream: api.stream,
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn(), resolve: () => ({ href: '/library' }) }) }))
vi.mock('ant-design-vue', () => ({ message: { error: vi.fn(), warning: vi.fn(), success: vi.fn() }, Modal: { confirm: vi.fn() } }))
import { getDailyPapers } from '@/services/api/daily'
import Library from '@/views/Library.vue'
import KnowledgeGraph from '@/views/KnowledgeGraph.vue'
import { useSearchAgentChat } from '@/composables/useSearchAgentChat'
import { useSearchConversations } from '@/composables/useSearchConversations'

function deferred<T = any>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
async function settle() { for (let i = 0; i < 8; i++) { await Promise.resolve(); await nextTick() } }
const apps: ReturnType<typeof createApp>[] = []
function mount(component: any) {
  const app = createApp(component)
  app.config.warnHandler = () => {}
  app.component('a-table', { template: '<div />' })
  const host = document.createElement('div'); document.body.append(host)
  apps.push(app)
  return (app.mount(host) as any).$.setupState
}
beforeEach(() => {
  vi.resetAllMocks()
  api.folders.mockResolvedValue({ success: true, folders: [] })
})
afterEach(() => {
  apps.splice(0).forEach(app => app.unmount())
  document.body.replaceChildren()
  vi.clearAllTimers(); vi.useRealTimers()
  localStorage.clear()
})

describe('Daily refresh', () => {
  const old = { success: true, arxiv_selected: [{ title: 'old' }], personalized: [] }
  it('waits for refresh completion and delivers the new list', async () => {
    const response = deferred()
    api.get.mockResolvedValue({ status: 200, data: old })
    api.post.mockReturnValue(response.promise)
    let settled = false
    const pending = getDailyPapers({ force_refresh: true }).then(r => { settled = true; return r })
    await settle()
    expect(settled).toBe(false)
    response.resolve({ data: { ...old, arxiv_selected: [{ title: 'new' }] } })
    expect((await pending).arxiv_selected[0].title).toBe('new')
  })
  it.each(['network', 'empty', 'unsuccessful'])('keeps the last list with an honest %s status', async (kind) => {
    api.get.mockResolvedValue({ status: 200, data: old })
    if (kind === 'network') api.post.mockRejectedValue(new Error('offline'))
    else api.post.mockResolvedValue({ data: { ...old, success: kind !== 'unsuccessful', arxiv_selected: [] } })
    const result = await getDailyPapers({ force_refresh: true })
    expect(result.arxiv_selected[0].title).toBe('old')
    expect(result.stale_cache).toBe(true)
    expect(!!result.refresh_failed).toBe(kind !== 'empty')
  })
})

describe('Asynchronous view identity', () => {
  it('loads the latest category while ignoring an older response', async () => {
    const a = deferred(), b = deferred()
    api.getLibrary.mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)
    const state = mount(Library)
    await settle()
    state.onCategoryClick({ key: 'B' })
    expect(api.getLibrary).toHaveBeenLastCalledWith(10, { offset: 0, category: 'B' })
    b.resolve({ success: true, papers: [{ id: 2, category: 'B' }], total: 1 }); await settle()
    a.resolve({ success: true, papers: [{ id: 1, category: 'A' }], total: 22 }); await settle()
    expect(state.papers[0].category).toBe('B')
    expect(state.pagination.total).toBe(1)
    expect(state.loading).toBe(false)
  })
  it('keeps graph details attached to the selected node', async () => {
    const a = deferred(), b = deferred()
    api.get.mockResolvedValue({ data: { success: true, nodes: [], edges: [] } })
    api.getPaper.mockImplementation((id: number) => id === 1 ? a.promise : b.promise)
    const state = mount(KnowledgeGraph); await settle()
    state.selected = { id: 'paper:1', type: 'paper', paper_id: 1, label: 'A' }; await settle()
    state.selected = { id: 'paper:2', type: 'paper', paper_id: 2, label: 'B' }; await settle()
    b.resolve({ id: 2, title: 'B' }); await settle()
    a.resolve({ id: 1, title: 'A' }); await settle()
    expect(state.selected.paper_id).toBe(2)
    expect(state.paperDetail.id).toBe(2)
    state.selected = null; await settle()
    expect(state.paperDetail).toBeNull()
  })
})

describe('Search conversation isolation', () => {
  it.each(['switch', 'new', 'delete'])('stores a late answer only in its originating conversation after %s', async (action) => {
    vi.useFakeTimers()
    const response = deferred()
    api.stream.mockReturnValue(response.promise)
    const messages = ref<any[]>([]), userInput = ref('query A'), isLoading = ref(false), hasSearched = ref(false)
    const conv = useSearchConversations({ messages, userInput, hasSearched, titleFromMessages: (m: any[]) => m[0]?.content || '' })
    conv.conversations.value.push({ id: 'B', title: 'B', timestamp: 1, messageCount: 2,
      messages: [{ role: 'user', content: 'query B' }, { role: 'assistant', content: 'answer B' }] })
    const chat = useSearchAgentChat({ messages, userInput, isLoading, hasSearched,
      ensureCurrentConversationId: conv.ensureCurrentConversationId, scrollToBottom: () => {},
      onConversationDirty: conv.saveConversationSnapshot })
    const pending = chat.sendMessage()
    const origin = conv.currentConversationId.value!
    expect(isLoading.value).toBe(true)
    if (action === 'switch') conv.loadConversation('B')
    else if (action === 'new') conv.createNewConversation()
    else conv.removeConversation(origin)
    userInput.value = 'unsent next question'
    const onEvent = api.stream.mock.calls[0][1]
    onEvent({ type: 'status', message: 'A still searching' })
    response.resolve({ success: true, response: 'answer A', papers: [] })
    await pending
    await vi.runAllTimersAsync()
    expect(userInput.value).toBe('unsent next question')
    expect(isLoading.value).toBe(false)
    if (action === 'switch') expect(messages.value.map(m => m.content)).toEqual(['query B', 'answer B'])
    else expect(messages.value).toEqual([])
    const saved = JSON.parse(localStorage.getItem('searchAgentConversations')!)
    expect(saved.find((c: any) => c.id === 'B').messages[1].content).toBe('answer B')
    if (action === 'delete') expect(saved.find((c: any) => c.id === origin)).toBeUndefined()
    else expect(saved.find((c: any) => c.id === origin).messages[1].content).toBe('answer A')
  })
})
