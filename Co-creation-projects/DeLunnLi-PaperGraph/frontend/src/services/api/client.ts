import axios from 'axios'
import { BACKEND_ORIGIN, BACKEND_PORT } from '@/config/ports'

export const API_BASE_URL = BACKEND_ORIGIN
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})
apiClient.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    const ax = err as {
      code?: string; message?: string
      response?: { data?: { detail?: unknown } }
      config?: { url?: string }
    }
    const msg0 = String(ax?.message ?? '')
    if (ax.code === 'ECONNABORTED' || /timeout of \d+ms exceeded/i.test(msg0)) {
      const rel = String(ax?.config?.url ?? '')
      let hint: string
      if (rel.includes('papers/daily')) {
        hint = '请求超时：每日论文冷路径（POST）会并行拉多源并做排序/个性化，可稍后重试或减少条数。'
      } else if (rel.includes('search-agent')) {
        hint = '请求超时：文献检索响应过久。请确认后端已运行，或改用更短、更具体的查询。'
      } else if (rel.includes('paper-reader/chat')) {
        hint = '请求超时：阅读助手响应过久（可能含相关论文检索）。请稍后重试。'
      } else {
        hint = `请求超时：请确认后端已运行（默认 ${BACKEND_PORT}）且通过 Vite 开发服务器访问。`
      }
      return Promise.reject(new Error(hint))
    }
    const detail = ax.response?.data?.detail
    if (detail != null) {
      let msg: string
      if (Array.isArray(detail)) {
        msg = detail.map((x: any) => (x?.msg ? String(x.msg) : JSON.stringify(x))).join('；')
      } else {
        msg = String(detail)
      }
      return Promise.reject(new Error(msg))
    }
    return Promise.reject(err instanceof Error ? err : new Error(String(ax?.message ?? '请求失败')))
  }
)
export default apiClient