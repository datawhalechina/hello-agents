import axios from 'axios'
import type { TripFormData, TripPlanResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 后端通过 HttpOnly Cookie 做认证，axios 需附带 cookie */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// 共享 Refresh Promise：多个 401 同时到来时共用一个刷新请求
let _refreshPromise: Promise<boolean> | null = null

/** 刷新Token（Cookie自动携带refresh_token） */
async function tryRefresh(): Promise<boolean> {
  try {
    const res = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {}, {
      withCredentials: true,
    })
    return res.status === 200
  } catch {
    return false
  }
}

/** 加锁执行刷新，同时段多个调用共享同一个 Promise */
function acquireRefreshLock(): Promise<boolean> {
  // 锁已被持有 → 返回同一个 promise，不发起新刷新
  if (_refreshPromise) return _refreshPromise

  // 加锁：创建新的刷新 promise，完成后自动释放锁
  _refreshPromise = tryRefresh().finally(() => {
    _refreshPromise = null
  })
  return _refreshPromise
}

/** 响应拦截器 — 401 自动刷新重试（刷新过程加锁，无竞态） */
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }
    originalRequest._retry = true

    // 获取刷新锁：第一个请求创建并持有锁（发起刷新）
    // 后续请求共享同一把锁（等刷新完成），不会重复发起
    const success = await acquireRefreshLock()

    if (success) {
      return apiClient(originalRequest)
    }

    // 刷新彻底失败 → 跳登录
    window.location.href = '/login'
    return Promise.reject(error)
  }
)


/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

// ============ 旅游AI对话 ============

export interface ChatSession {
  id: number
  user_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/**
 * 获取会话列表
 */
export async function getChatSessions(): Promise<{ success: boolean; sessions: ChatSession[] }> {
  const response = await apiClient.get('/api/chat/sessions')
  return response.data
}

/**
 * 创建新会话
 */
export async function createChatSession(): Promise<{ success: boolean; session: ChatSession }> {
  const response = await apiClient.post('/api/chat/sessions')
  return response.data
}

/**
 * 删除会话
 */
export async function deleteChatSession(sessionId: number): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete(`/api/chat/sessions/${sessionId}`)
  return response.data
}

/**
 * 获取会话消息
 */
export async function getChatMessages(sessionId: number): Promise<{ success: boolean; messages: ChatMessage[] }> {
  const response = await apiClient.get(`/api/chat/sessions/${sessionId}/messages`)
  return response.data
}

/**
 * 发送消息
 */
export async function sendChatMessage(sessionId: number, content: string): Promise<{ success: boolean; reply: string }> {
  const response = await apiClient.post(`/api/chat/sessions/${sessionId}/messages`, { content })
  return response.data
}

export default apiClient
