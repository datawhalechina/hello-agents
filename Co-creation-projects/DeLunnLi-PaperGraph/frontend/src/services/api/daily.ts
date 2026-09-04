import { apiClient } from './client'
import type { Paper } from '@/types'
interface DailyPaperPickHint {
  identity_key: string; pick_kind: string; explanation: string
}
export interface DailyPapersApiResponse {
  success: boolean; date_key: string
  arxiv_latest_total: number; arxiv_selected_total: number; personalized_total: number
  arxiv_latest: Paper[]; arxiv_selected: Paper[]; personalized: Paper[]
  message?: string | null; memory_keywords_used?: string[]
  stale_cache?: boolean; refresh_failed?: boolean
  strategy_explanation?: string
  personalized_theme_keywords?: string[]; general_theme_keywords?: string[]
  personalized_pick_hints?: DailyPaperPickHint[]; general_pick_hints?: DailyPaperPickHint[]
}
const DAILY_PAPERS_REQUEST_MS = 420000
function dailyPayloadCount(data?: DailyPapersApiResponse | null): number {
  return (data?.arxiv_selected?.length ?? 0) + (data?.personalized?.length ?? 0)
}
async function getCachedDailyPapers(): Promise<DailyPapersApiResponse | null> {
  const res = await apiClient.get<DailyPapersApiResponse>('/api/papers/daily', {
    params: { _t: Date.now() },
    headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
    validateStatus: (s) => s === 200 || s === 204,
    timeout: DAILY_PAPERS_REQUEST_MS,
  })
  return res.status === 200 && res.data?.success ? res.data : null
}
export async function getDailyPapers(body?: {
  days_back?: number; arxiv_max_results?: number; arxiv_categories?: string[]
  personalized_k?: number; library_limit?: number; force_refresh?: boolean
  use_llm_theme_keywords?: boolean
}): Promise<DailyPapersApiResponse> {
  const cached = await getCachedDailyPapers().catch(() => null)

  if (!body?.force_refresh) {
    if (dailyPayloadCount(cached) > 0) return cached as DailyPapersApiResponse
  }

  // Show cache while a forced refresh runs in the background.
  if (body?.force_refresh && dailyPayloadCount(cached) > 0) {
    apiClient.post<DailyPapersApiResponse>('/api/papers/daily', body, {
      timeout: DAILY_PAPERS_REQUEST_MS,
    }).then(postRes => {
      if (dailyPayloadCount(postRes.data) > 0) {
        return postRes.data
      }
      return null
    }).catch(() => null)
    return { ...(cached as DailyPapersApiResponse), message: '正在后台刷新…当前显示最近缓存。' }
  }

  try {
    const postRes = await apiClient.post<DailyPapersApiResponse>('/api/papers/daily', body || {}, {
      timeout: DAILY_PAPERS_REQUEST_MS,
    })
    if (body?.force_refresh && dailyPayloadCount(postRes.data) === 0) {
      if (dailyPayloadCount(cached) > 0) {
        return { ...(cached as DailyPapersApiResponse), stale_cache: true, message: postRes.data?.message || '刷新未取到新结果，已显示缓存列表。' }
      }
    }
    return postRes.data
  } catch (err) {
    if (body?.force_refresh && dailyPayloadCount(cached) > 0) {
      return { ...(cached as DailyPapersApiResponse), stale_cache: true, refresh_failed: true, message: '刷新失败，已显示上次缓存结果。' }
    }
    throw err
  }
}
type FeedbackAction = 'click' | 'save' | 'skip' | 'ignore' | 'read'
interface DailyRecommendFeedbackRequest {
  identity_key: string; title?: string; action: FeedbackAction
  source_list?: 'personalized' | 'general'; score_at_recommend?: number
  keywords?: string[]; category?: string; journal?: string; source?: string
}
export async function postDailyRecommendFeedback(
  body: DailyRecommendFeedbackRequest
): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post('/api/papers/daily/feedback', body)
  return response.data
}
