import { backendLocalhostUrl } from '@/config/ports'
import { apiClient, API_BASE_URL } from './client'
import type { Paper } from '@/types'
interface SearchAgentRequest {
  message: string; mode?: 'accuracy' | 'novelty'; use_tavily?: boolean
  history?: Array<{ role: string; content: string }>
}
interface ToolCall {
  name: string; status: 'running' | 'success' | 'error'
  params?: Record<string, unknown>; result_summary?: string
}
interface SearchAgentResponse {
  success: boolean; response: string; total: number
  search_params?: { query: string; keywords: string[]; venues: string[]; year_from?: number; year_to?: number; sort: string; mode: string }
  tool_calls?: ToolCall[]; papers?: Paper[]; message?: string
}
const SEARCH_AGENT_REQUEST_MS = 420000

function streamHttpErrorMessage(status: number, bodyText: string): string {
  const detail = bodyText?.trim()
  if (status === 422) {
    return detail
      ? `请求参数无效：${detail.slice(0, 200)}`
      : '请求参数无效，请缩短或修改搜索内容后重试。'
  }
  if (status === 504) {
    return '检索超时：后端仍在处理或 LLM/多源召回过慢，请稍后重试或缩短描述。'
  }
  if (status === 502 || status === 503) {
    return `无法连接检索服务：请确认后端已启动（默认 ${backendLocalhostUrl()}）。`
  }
  if (status >= 500) {
    return detail ? `服务端错误（${status}）：${detail.slice(0, 160)}` : `服务端错误（${status}），请查看后端日志。`
  }
  return detail ? `请求失败（${status}）：${detail.slice(0, 160)}` : `请求失败（HTTP ${status}）`
}

export type SearchAgentStreamEvent =
  | { type: 'status'; ts_ms?: number; message?: string }
  | { type: 'tool_call'; ts_ms?: number; tool?: string; parameters?: any; result?: any }
  | { type: 'final'; ts_ms?: number; elapsed_ms?: number; success?: boolean }
  | { type: 'error'; ts_ms?: number; message?: string }
  | { type: 'final_result'; ts_ms?: number; result: SearchAgentResponse }
export async function searchAgentChatStream(
  request: SearchAgentRequest,
  onEvent: (ev: SearchAgentStreamEvent) => void,
): Promise<SearchAgentResponse> {
  const base = (apiClient.defaults.baseURL || API_BASE_URL).replace(/\/$/, '')
  const url = `${base}/api/papers/search-agent/stream`
  const ctrl = new AbortController()
  const timer = window.setTimeout(() => ctrl.abort(), SEARCH_AGENT_REQUEST_MS)
  try {
    const resp = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal: ctrl.signal,
    })
    if (!resp.ok) {
      const errBody = await resp.text().catch(() => '')
      throw new Error(streamHttpErrorMessage(resp.status, errBody))
    }
    if (!resp.body) {
      throw new Error('检索流响应为空，请确认后端版本与 /api/papers/search-agent/stream 是否正常。')
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    let lastFinal: SearchAgentResponse | null = null
    let lastStreamError: string | null = null
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      while (true) {
        let idx = buf.indexOf('\n\n'); let sepLen = 2
        const idx2 = buf.indexOf('\r\n\r\n')
        if (idx < 0 || (idx2 >= 0 && idx2 < idx)) { idx = idx2; sepLen = 4 }
        if (idx < 0) break
        const chunk = buf.slice(0, idx); buf = buf.slice(idx + sepLen)
        const dataLines = chunk.split(/\r?\n/).map((s) => s.trim()).filter((s) => s.startsWith('data:'))
        for (const line of dataLines) {
          const jsonStr = line.replace(/^data:\s*/, '')
          if (!jsonStr) continue
          try {
            const ev = JSON.parse(jsonStr) as SearchAgentStreamEvent
            onEvent(ev)
            if (ev?.type === 'error' && ev.message) lastStreamError = String(ev.message)
            if (ev?.type === 'final_result' && ev?.result) {
              lastFinal = ev.result
              return ev.result
            }
          } catch { /* ignore malformed chunk */ }
        }
      }
    }
    const tail = buf.trim()
    if (tail.includes('data:')) {
      for (const line of tail.split(/\r?\n/).map((s) => s.trim()).filter((s) => s.startsWith('data:'))) {
        const jsonStr = line.replace(/^data:\s*/, '')
        if (!jsonStr) continue
        try {
          const ev = JSON.parse(jsonStr) as SearchAgentStreamEvent
          onEvent(ev)
          if (ev?.type === 'error' && ev.message) lastStreamError = String(ev.message)
          if (ev?.type === 'final_result' && ev?.result) {
            lastFinal = ev.result
            return ev.result
          }
        } catch { /* ignore malformed chunk */ }
      }
    }
    if (lastFinal) return lastFinal
    if (lastStreamError) {
      throw new Error(lastStreamError)
    }
    throw new Error('检索流已结束但未收到最终结果，请重试；若频繁出现请查看后端是否重启或超时。')
  } catch (e: unknown) {
    if (e instanceof Error && e.name === 'AbortError') {
      throw new Error('检索已取消或超时（约 7 分钟），请缩短查询或稍后重试。')
    }
    throw e
  } finally {
    window.clearTimeout(timer)
  }
}