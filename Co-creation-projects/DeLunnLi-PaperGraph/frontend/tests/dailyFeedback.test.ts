import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
const api = vi.hoisted(() => ({ daily: vi.fn(), feedback: vi.fn() }))
vi.mock('@/services/api', () => ({ getDailyPapers: api.daily, postDailyRecommendFeedback: api.feedback, savePapers: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('ant-design-vue', () => ({ message: { success: vi.fn(), info: vi.fn(), warning: vi.fn(), error: vi.fn() }, Modal: { confirm: vi.fn() } }))
vi.mock('@/components/shared/PaperCard.vue', () => ({ default: { template: '<div />' } }))
import DailyArxiv from '@/views/DailyArxiv.vue'

let app: ReturnType<typeof createApp> | undefined
beforeEach(() => { vi.resetAllMocks(); api.feedback.mockResolvedValue({ success: true }) })
afterEach(() => { app?.unmount(); app = undefined; document.body.replaceChildren() })

it.each([
  [{ title: 'Paper', arxiv_id: '2609.00001v2', year: 2026 }, 'arxiv:2609.00001'],
  [{ title: 'Paper', doi: '10.1234/ABC', year: 2026 }, 'doi:10.1234/abc'],
  [{ title: 'Title_Only', year: 2026 }, 'ty:title_only|2026'],
  [{ title: 'Unknown Year', year: null }, 'ty:unknown year|0'],
])('sends the actual daily UI identity, matches hints and filters skipped items: %s', async (paper, identity) => {
  const response = {
    success: true, date_key: '2026-09-26', arxiv_selected: [paper], personalized: [],
    personalized_total: 0, arxiv_selected_total: 1,
    general_pick_hints: [{ identity_key: identity, pick_kind: 'general', explanation: 'General recommendation' }],
  }
  api.daily.mockResolvedValue(response)
  app = createApp(DailyArxiv); app.config.warnHandler = () => {}
  const host = document.createElement('div'); document.body.append(host)
  const state = (app.mount(host) as any).$.setupState
  for (let i = 0; i < 8; i++) { await Promise.resolve(); await nextTick() }
  expect(state.hintFor(paper)?.explanation).toBe('General recommendation')
  expect(state.randomIds.has(identity)).toBe(true)
  await state.skipOne(paper, 0)
  expect(api.feedback).toHaveBeenCalledWith(expect.objectContaining({ identity_key: identity, action: 'skip', source_list: 'general' }))
  state.applyDailyPayload(response)
  expect(state.searchResults).toEqual([])
})
