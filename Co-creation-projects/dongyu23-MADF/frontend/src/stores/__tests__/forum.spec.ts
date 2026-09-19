import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import request from '@/utils/request'
import { useForumStore } from '../forum'

vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

describe('forum store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('treats an unauthorized forum response as an expected navigation state', async () => {
    vi.mocked(request.get).mockRejectedValue({ response: { status: 403 } })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const store = useForumStore()

    await store.fetchForum(3)

    expect(store.currentForum).toBeNull()
    expect(consoleError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it('keeps diagnostics for an unexpected forum loading failure', async () => {
    vi.mocked(request.get).mockRejectedValue(new Error('network unavailable'))
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const store = useForumStore()

    await store.fetchForum(3)

    expect(consoleError).toHaveBeenCalledWith('Failed to fetch forum 3:', expect.any(Error))
    consoleError.mockRestore()
  })

  it('never writes the JWT-bearing WebSocket URL to the console', () => {
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const socket = { readyState: WebSocket.CONNECTING } as WebSocket
    const webSocket = vi.spyOn(window, 'WebSocket').mockImplementation(() => socket)
    localStorage.setItem('token', 'secret-token')
    const store = useForumStore()

    store.connectWebSocket(42)

    expect(consoleLog).toHaveBeenCalledWith('[WS Global] Connecting to forum 42')
    expect(consoleLog).not.toHaveBeenCalledWith(expect.stringContaining('secret-token'))
    webSocket.mockRestore()
    consoleLog.mockRestore()
  })

  it('deduplicates persisted and WebSocket system logs', () => {
    const store = useForumStore()
    const log = {
      id: 8,
      timestamp: '2026-08-12T21:18:35.439Z',
      level: 'info' as const,
      source: 'System',
      content: '所有参与者正在思考中...',
    }

    store.addSystemLog(log)
    const { id: _id, ...cachedLog } = log
    store.addSystemLog(cachedLog)

    expect(store.systemLogs).toEqual([log])
  })

  it('uses the authoritative start time returned by the start endpoint', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: {
        status: 'started',
        start_time: '2026-08-13T08:00:00',
        duration_minutes: 30,
      },
    })
    const store = useForumStore()
    store.currentForum = {
      id: 7,
      topic: '30 minute test',
      creator_id: 1,
      status: 'pending',
      start_time: null,
      summary_history: [],
      duration_minutes: 30,
    }

    await store.startForum(7)

    expect(store.currentForum.status).toBe('running')
    expect(store.currentForum.start_time).toBe('2026-08-13T08:00:00')
    expect(store.currentForum.duration_minutes).toBe(30)
  })

  it('submits an exact 30 minute duration when creating a forum', async () => {
    vi.mocked(request.post).mockResolvedValue({
      data: {
        id: 8,
        topic: 'duration test',
        creator_id: 1,
        status: 'pending',
        start_time: null,
        summary_history: [],
        duration_minutes: 30,
      },
    })
    const store = useForumStore()

    await store.createForum('duration test', [2, 3], 30)

    expect(request.post).toHaveBeenCalledWith('/forums/', {
      topic: 'duration test',
      participant_ids: [2, 3],
      moderator_id: undefined,
      duration_minutes: 30,
    })
  })
})
