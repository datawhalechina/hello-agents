import type { RecommendRequest, RecommendResponse } from '../types'
import { apiFetch } from './client'

export function postRecommend(body: RecommendRequest): Promise<RecommendResponse> {
  return apiFetch<RecommendResponse>('/api/recommend', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
