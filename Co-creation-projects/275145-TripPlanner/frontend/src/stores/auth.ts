import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, AuthState } from '@/types'
import { authApi } from '@/services/api'

/**
 * 认证状态管理
 * 使用Pinia进行状态管理，支持localStorage持久化
 */
export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userId = computed(() => user.value?.user_id || null)
  const username = computed(() => user.value?.username || '')

  /**
   * 设置认证信息
   * @param accessToken JWT访问令牌
   * @param userInfo 用户信息
   */
  const setAuth = (accessToken: string, userInfo: User) => {
    token.value = accessToken
    user.value = userInfo
    
    // 保存到localStorage
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user_info', JSON.stringify(userInfo))
  }

  /**
   * 退出登录
   */
  const logout = async () => {
    try {
      // 调用后端logout API（如果需要记录退出日志等）
      // 即使API调用失败，也要清除本地认证信息
      try {
        await authApi.logout()
      } catch (apiError) {
        console.error('后端logout API调用失败:', apiError)
        // 不抛出错误，继续清除本地认证信息
      }
    } finally {
      // 无论如何都要清除本地认证信息
      clearAuth()
    }
  }

  /**
   * 清除认证信息
   */
  const clearAuth = () => {
    token.value = null
    user.value = null
    
    // 清除localStorage
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  }

  /**
   * 从localStorage恢复认证状态
   */
  const restoreAuth = () => {
    try {
      const savedToken = localStorage.getItem('access_token')
      const savedUserInfo = localStorage.getItem('user_info')
      
      if (savedToken && savedUserInfo) {
        token.value = savedToken
        user.value = JSON.parse(savedUserInfo)
      }
    } catch (error) {
      console.error('恢复认证状态失败:', error)
      clearAuth()
    }
  }

  /**
   * 更新用户信息
   * @param updatedUser 更新后的用户信息
   */
  const updateUser = (updatedUser: Partial<User>) => {
    if (user.value) {
      user.value = { ...user.value, ...updatedUser }
      localStorage.setItem('user_info', JSON.stringify(user.value))
    }
  }

  // 初始化时恢复认证状态
  restoreAuth()

  return {
    // 状态
    token,
    user,
    
    // 计算属性
    isAuthenticated,
    userId,
    username,
    
    // 方法
    setAuth,
    logout,
    clearAuth,
    restoreAuth,
    updateUser
  }
})