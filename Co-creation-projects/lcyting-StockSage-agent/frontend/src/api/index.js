import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** 失败自动重试（指数退避）；可在单次请求上设置 config.skipRetry = true 关闭 */
const RETRY_MAX = 2
const RETRY_BASE_DELAY_MS = 600

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 是否应对本次错误进行重试（已在拦截器内检查次数）
 * - GET/HEAD：超时、无响应、429、5xx
 * - POST/PUT/PATCH/DELETE：仅超时、无响应（避免收到 HTTP 响应后重复提交）
 */
function shouldRetryRequest(error) {
  const cfg = error.config
  if (!cfg || cfg.skipRetry) return false

  const method = (cfg.method || 'get').toLowerCase()
  const status = error.response?.status

  const noResponse = !error.response
  const timedOut = error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')

  if (method === 'get' || method === 'head') {
    if (noResponse || timedOut) return true
    if (status === 429) return true
    if (status >= 500 && status <= 599) return true
    return false
  }

  return noResponse || timedOut
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 妙想额度用尽提示（节流，避免同页多次请求刷屏）
let _lastMxQuotaWarnAt = 0
const MX_QUOTA_WARN_COOLDOWN_MS = 60_000

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body?.code === 0 && body?.meta?.quota_exhausted) {
      const now = Date.now()
      if (now - _lastMxQuotaWarnAt >= MX_QUOTA_WARN_COOLDOWN_MS) {
        _lastMxQuotaWarnAt = now
        ElMessage.warning(body.meta.hint || body.message || '今日妙想调用额度已用尽，当前为缓存数据')
      }
    }
    return body
  },
  async (error) => {
    if (error.code === 'ERR_CANCELED') {
      return Promise.reject(error)
    }

    const cfg = error.config
    const count = cfg ? cfg.__retryCount || 0 : 0

    if (cfg && count < RETRY_MAX && shouldRetryRequest(error)) {
      cfg.__retryCount = count + 1
      const delay = RETRY_BASE_DELAY_MS * Math.pow(2, count)
      if (import.meta.env.DEV) {
        console.warn(
          `[api] 请求失败，${delay}ms 后进行第 ${cfg.__retryCount}/${RETRY_MAX} 次重试:`,
          cfg.method,
          cfg.url,
          error.message || error.code || ''
        )
      }
      await sleep(delay)
      try {
        return await api.request(cfg)
      } catch (e) {
        console.error('API请求错误:', e)
        return Promise.reject(e)
      }
    }

    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

export default api

/**
 * 低层流式 POST（不做 axios 封装），路径需含 /api/v1 前缀或传入绝对 URL。
 */
export function streamRequest(url, body, options = {}) {
  const path = url.startsWith('http')
    ? url
    : `/api/v1${url.startsWith('/') ? url : `/${url}`}`
  const { headers, ...rest } = options
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body ?? {}),
    ...rest,
  })
}

/** 历史记录 REST（非流式） */
export const historyApi = {
  list: (params = {}) => api.get('/history/list', { params }),
  detail: (id) => api.get(`/history/${id}`),
  delete: (id) => api.delete(`/history/${id}`),
  clear: (params = {}) => api.post('/history/clear', {}, { params }),
}

/**
 * fetch 仅在抛错（网络中断、DNS 等）时重试；HTTP 4xx/5xx 仍返回 Response，由调用方处理。
 */
export async function fetchWithRetry(url, options = {}, maxRetries = RETRY_MAX) {
  let lastErr
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetch(url, options)
    } catch (e) {
      lastErr = e
      if (attempt < maxRetries) {
        const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt)
        if (import.meta.env.DEV) {
          console.warn(
            `[fetch] 网络失败，${delay}ms 后第 ${attempt + 1}/${maxRetries} 次重试:`,
            url
          )
        }
        await sleep(delay)
      }
    }
  }
  throw lastErr
}

/** 单次请求关闭自动重试：api.get(url, { skipRetry: true }) */
export { RETRY_MAX, RETRY_BASE_DELAY_MS }
