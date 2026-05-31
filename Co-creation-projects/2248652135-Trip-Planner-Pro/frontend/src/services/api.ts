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

// 是否正在刷新Token
let _refreshing = false
let _refreshQueue: Array<{
  resolve: () => void
  reject: (err: any) => void
}> = []

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

/** 跳转到登录页 */
function redirectLogin() {
  window.location.href = '/login'
}

/** 响应拦截器 — 401 自动刷新重试 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }
    originalRequest._retry = true

    if (_refreshing) {
      // 已有刷新在进行中，排队等待
      return new Promise((resolve, reject) => {
        _refreshQueue.push({
          resolve: () => resolve(apiClient(originalRequest)),
          reject,
        })
      })
    }

    _refreshing = true
    const success = await tryRefresh()
    _refreshing = false

    if (success) {
      const queue = _refreshQueue
      _refreshQueue = []
      queue.forEach((q) => q.resolve())
      return apiClient(originalRequest)
    }

    // 刷新失败
    _refreshQueue.forEach((q) => q.reject(error))
    _refreshQueue = []
    redirectLogin()
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

export default apiClient
