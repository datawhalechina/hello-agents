import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, reactive } from 'vue'
const api = vi.hoisted(() => ({
  route: null as any, getPaper: vi.fn(), history: vi.fn(), opening: vi.fn(), chat: vi.fn(),
  log: vi.fn(), exitLog: vi.fn(), httpPost: vi.fn(),
}))
vi.mock('@/services/api', () => ({
  getPaper: api.getPaper, getLibraryPdfHref: (id: number) => `/pdf/${id}`,
  getPaperReaderHistory: api.history, postPaperReaderOpening: api.opening, postPaperReaderChat: api.chat,
  postReadingLog: api.log, sendReadingLogOnExit: api.exitLog, savePapers: vi.fn(),
}))
vi.mock('@/services/api/client', () => ({ apiClient: { defaults: { baseURL: 'https://api.example' }, post: api.httpPost } }))
vi.mock('vue-router', () => ({ useRoute: () => api.route, useRouter: () => ({ push: vi.fn() }) }))
vi.mock('ant-design-vue', () => ({ message: { error: vi.fn(), warning: vi.fn(), success: vi.fn() } }))
vi.mock('@/components/PdfJsViewer.vue', async () => {
  const { defineComponent, onMounted, h } = await import('vue')
  return { default: defineComponent({
    emits: ['loaded'],
    setup(_, { emit }) { onMounted(() => emit('loaded')); return () => h('div') },
  }) }
})
import PaperReader from '@/views/PaperReader.vue'
import { sendReadingLogOnExit } from '@/services/api/papers'

function deferred<T = any>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}
async function settle() { for (let i = 0; i < 10; i++) { await Promise.resolve(); await nextTick() } }
let app: ReturnType<typeof createApp> | undefined
function mount() {
  app = createApp(PaperReader); app.config.warnHandler = () => {}
  const host = document.createElement('div'); document.body.append(host)
  return (app.mount(host) as any).$.setupState
}
beforeEach(() => {
  vi.resetAllMocks()
  api.route = reactive({ params: { id: '1' }, query: { standalone: '1' } })
  api.getPaper.mockImplementation(async (id: number) => ({ id, title: `Paper ${id}` }))
  api.history.mockResolvedValue({ success: true, turns: [{ role: 'assistant', content: 'saved history' }] })
  api.opening.mockResolvedValue({ success: true, opening: 'opening' })
  api.log.mockResolvedValue({ success: true })
})
afterEach(() => {
  app?.unmount(); app = undefined
  document.body.replaceChildren()
  vi.clearAllTimers(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals()
})

describe('Reader request isolation', () => {
  it('keeps metadata and PDF attached to the new route after out-of-order loading', async () => {
    const a = deferred(), b = deferred()
    api.getPaper.mockImplementation((id: number) => id === 1 ? a.promise : b.promise)
    const state = mount(); await settle()
    api.route.params.id = '2'; await settle()
    b.resolve({ id: 2, title: 'B', local_pdf_path: 'b.pdf' }); await settle()
    a.resolve({ id: 1, title: 'A', local_pdf_path: 'a.pdf' }); await settle()
    expect(state.paperId).toBe(2)
    expect(state.paper.id).toBe(2)
    expect(state.pdfSrc).toBe('/pdf/2')
    expect(api.history).toHaveBeenCalled()
    expect(api.history.mock.calls.every(([id]) => id === 2)).toBe(true)
  })
  it('does not insert an old chat answer into a new paper', async () => {
    const a = deferred()
    api.chat.mockReturnValue(a.promise)
    const state = mount(); await settle()
    state.draft = 'question about A'
    const pending = state.send(); await settle()
    expect(api.chat).toHaveBeenCalledWith(expect.objectContaining({ paper_id: 1 }))
    api.route.params.id = '2'; await settle()
    a.resolve({ success: true, reply: 'A private answer', pdf_parsing: true }); await pending
    expect(state.messages.map((m: any) => m.content)).toEqual(['saved history'])
    expect(state.sending).toBe(false)
    expect(state.pdfParsing).toBe(false)
  })
  it('does not add an old opening after switching papers', async () => {
    const a = deferred()
    api.history.mockResolvedValue({ success: true, turns: [] })
    api.opening.mockImplementation((id: number) => id === 1 ? a.promise : Promise.resolve({ success: true, opening: 'B opening' }))
    const state = mount(); await settle()
    api.route.params.id = '2'; await settle()
    a.resolve({ success: true, opening: 'A opening', pdf_parsing: true }); await settle()
    expect(state.messages.map((m: any) => m.content)).toEqual(['B opening'])
    expect(state.pdfParsing).toBe(false)
  })
  it('history loading does not erase a question sent while it was pending', async () => {
    const history = deferred(), chat = deferred()
    api.history.mockReturnValue(history.promise)
    api.chat.mockReturnValue(chat.promise)
    const state = mount(); await settle()
    state.draft = 'new question'
    const pending = state.send(); await settle()
    history.resolve({ success: true, turns: [{ role: 'assistant', content: 'old answer' }] }); await settle()
    expect(state.messages.some((m: any) => m.content === 'new question')).toBe(true)
    chat.resolve({ success: true, reply: 'new answer' }); await pending
    expect(state.messages.some((m: any) => m.content === 'new answer')).toBe(true)
  })
  it('waits for stored history after PDF loaded, then refreshes only the stale opening', async () => {
    const history = deferred()
    api.getPaper.mockResolvedValue({ id: 1, title: 'Paper', local_pdf_path: 'paper.pdf' })
    const turns = [
      { role: 'assistant', content: 'old opening' }, { role: 'user', content: 'saved question' },
      { role: 'assistant', content: 'saved answer' },
    ]
    api.history.mockReturnValueOnce(history.promise).mockResolvedValue({
      success: true, turns: [{ role: 'assistant', content: 'new opening' }, ...turns.slice(1)],
    })
    api.opening.mockResolvedValue({ success: true, opening: 'new opening' })
    const state = mount(); await settle()
    expect(state.pdfReady).toBe(true)
    expect(api.opening).not.toHaveBeenCalled()
    history.resolve({ success: true, turns }); await settle()
    expect(api.opening).toHaveBeenCalledWith(1)
    expect(state.messages.map((m: any) => m.content)).toEqual(['new opening', 'saved question', 'saved answer'])
  })
})

describe('Reading duration delivery', () => {
  it('persists periodically and on tab exit using one cumulative session identity', async () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date('2026-09-26T10:00:00Z'))
    const close = vi.spyOn(window, 'close').mockImplementation(() => {})
    const state = mount(); await settle()
    await vi.advanceTimersByTimeAsync(30_000)
    expect(api.log).toHaveBeenLastCalledWith(expect.objectContaining({ paper_id: 1, duration_sec: 30 }))
    const id = api.log.mock.calls[0][0].session_id
    await vi.advanceTimersByTimeAsync(30_000)
    expect(api.log).toHaveBeenLastCalledWith(expect.objectContaining({ session_id: id, duration_sec: 60 }))
    vi.setSystemTime(new Date('2026-09-26T10:02:00Z'))
    state.closeTab(); window.dispatchEvent(new Event('pagehide'))
    expect(close).toHaveBeenCalledOnce()
    expect(api.exitLog).toHaveBeenLastCalledWith(expect.objectContaining({ session_id: id, paper_id: 1, duration_sec: 120 }))
    app!.unmount(); app = undefined
    const calls = api.exitLog.mock.calls.length
    await vi.advanceTimersByTimeAsync(30_000)
    window.dispatchEvent(new Event('pagehide'))
    expect(api.exitLog).toHaveBeenCalledTimes(calls)
  })
  it('starts a new session identity on the next paper and flushes the old paper', async () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date('2026-09-26T10:00:00Z'))
    mount(); await settle()
    vi.setSystemTime(new Date('2026-09-26T10:01:00Z'))
    api.route.params.id = '2'; await settle()
    const old = api.exitLog.mock.calls[0][0]
    expect(old).toMatchObject({ paper_id: 1, duration_sec: 60 })
    vi.setSystemTime(new Date('2026-09-26T10:02:00Z'))
    window.dispatchEvent(new Event('pagehide'))
    const current = api.exitLog.mock.calls.at(-1)![0]
    expect(current).toMatchObject({ paper_id: 2, duration_sec: 60 })
    expect(current.session_id).not.toBe(old.session_id)
  })
  it.each([true, false])('uses the configured backend with beacon available=%s', async (available) => {
    const beacon = vi.fn().mockReturnValue(available)
    vi.stubGlobal('navigator', { sendBeacon: beacon })
    const fetchMock = vi.fn().mockResolvedValue({ ok: true }); vi.stubGlobal('fetch', fetchMock)
    const body = { paper_id: 1, duration_sec: 60, session_id: 'reading-session' }
    sendReadingLogOnExit(body)
    expect(beacon).toHaveBeenCalledWith('https://api.example/api/papers/reading/log', expect.any(Blob))
    if (available) expect(fetchMock).not.toHaveBeenCalled()
    else expect(fetchMock).toHaveBeenCalledWith('https://api.example/api/papers/reading/log', expect.objectContaining({ keepalive: true, body: JSON.stringify(body) }))
  })
})
