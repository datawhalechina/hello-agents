import axios from 'axios'
import { message } from 'ant-design-vue'

const request = axios.create({
  // Base URL for the API
  baseURL: '/api/v1',
  timeout: 60000 // Increased timeout to 60s
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.dispatchEvent(new Event('madf-auth-changed'))
        if (!window.location.pathname.includes('/auth/login')) {
          message.error('会话已过期，请重新登录')
        }
      } else if (error.response.status >= 500) {
        // Log detailed error for debugging
        // Use JSON.stringify to safely print object content
        console.error('Server Error:', JSON.stringify(error.response.data, null, 2))
        message.error('服务器内部错误，请稍后重试')
      } else {
        const detail = error.response.data?.detail
        const msg = typeof detail === 'string' ? detail : (detail?.message || '请求失败')
        message.error(msg)
      }
    } else if (error.request) {
        message.error('网络连接失败，请检查网络设置')
    } else {
        message.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request
