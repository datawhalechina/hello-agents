import { apiUrl, get, post } from './http'
import type { DashboardStats, KeywordActionOut, SearchCreate, SearchJob, SearchListItem, SearchOut } from '@/types'

export function createSearchJob(payload: SearchCreate): Promise<SearchJob> {
  return post<SearchJob>('/search/jobs', payload)
}

export function getSearchJob(jobId: string): Promise<SearchJob> {
  return get<SearchJob>(`/search/jobs/${jobId}`)
}

export function cancelSearchJob(jobId: string): Promise<SearchJob> {
  return post<SearchJob>(`/search/jobs/${jobId}/cancel`, {})
}

export function openSearchJobEvents(
  jobId: string,
  onJob: (job: SearchJob) => void,
  onDisconnect: (error: Error) => void
): EventSource {
  const source = new EventSource(apiUrl(`/search/jobs/${jobId}/events`))
  source.onmessage = (event) => {
    try {
      onJob(JSON.parse(event.data) as SearchJob)
    } catch {
      source.close()
      onDisconnect(new Error('Invalid SSE progress event'))
    }
  }
  source.onerror = () => {
    source.close()
    onDisconnect(new Error('SSE progress stream disconnected'))
  }
  return source
}

export function getSearch(id: number): Promise<SearchOut> {
  return get<SearchOut>(`/search/${id}`)
}

export function getHistory(limit = 20): Promise<SearchListItem[]> {
  return get<SearchListItem[]>(`/search/history?limit=${limit}`)
}
export function getSearchStats(): Promise<DashboardStats> {
  return get<DashboardStats>('/search/stats')
}

export function excludeKeyword(keyword: string): Promise<KeywordActionOut> {
  return post<KeywordActionOut>('/search/keywords/exclude', { keyword })
}

export function restoreKeyword(keyword: string): Promise<KeywordActionOut> {
  return post<KeywordActionOut>('/search/keywords/restore', { keyword })
}

export function restoreAllKeywords(): Promise<KeywordActionOut> {
  return post<KeywordActionOut>('/search/keywords/restore-all', {})
}
