// Lightweight fetch wrapper around the FastAPI backend.
// In development the Vite server proxies /api -> http://localhost:8000.

import { ElMessage } from 'element-plus/es/components/message/index'

const BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export function apiUrl(path: string): string {
  return `${BASE}${path}`
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(apiUrl(path), {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    })
  } catch (err) {
    throw new ApiError(0, `无法连接后端服务：${(err as Error).message}`)
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      if (body && body.detail) detail = String(body.detail)
    } catch {
      /* non-JSON error body: keep default message */
    }
    throw new ApiError(resp.status, detail)
  }

  return (await resp.json()) as T
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export function notifyError(err: unknown): void {
  if (err instanceof ApiError) {
    ElMessage.error(err.message)
  } else {
    ElMessage.error('请求失败，请稍后重试')
  }
}
