/**
 * 用户偏好 Pinia Store
 *
 * 管理用户投资偏好的前端状态，支持：
 * - 从后端API加载偏好
 * - 本地localStorage兜底
 * - 偏好更新同步
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

// 本地存储的key
const LOCAL_STORAGE_KEY = 'stock_analyzer_preferences'

// 默认偏好
const DEFAULT_PREFERENCES = {
  risk_tolerance: 'moderate',
  investment_style: 'blend',
  investment_horizon: 'medium',
  target_return_rate: 10.0,
  max_position_ratio: 30.0,
  max_drawdown_limit: -15.0,
  notification_enabled: true,
  notification_channels: ['push'],
  market_alert_threshold: 5.0,
  language: 'zh',
  theme: 'auto',
  default_view: 'dashboard',
  preferred_sectors: [],
  excluded_sectors: [],
}

export const usePreferencesStore = defineStore('preferences', () => {
  // =========================================================================
  // 状态
  // =========================================================================
  const preferences = ref({ ...DEFAULT_PREFERENCES })
  const profile = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // =========================================================================
  // 计算属性
  // =========================================================================
  const riskLabel = computed(() => {
    const map = { conservative: '保守型', moderate: '稳健型', aggressive: '激进型' }
    return map[preferences.value.risk_tolerance] || preferences.value.risk_tolerance
  })

  const styleLabel = computed(() => {
    const map = { value: '价值投资', growth: '成长投资', momentum: '动量投资', dividend: '股息投资', blend: '混合风格' }
    return map[preferences.value.investment_style] || preferences.value.investment_style
  })

  const isConfigured = computed(() => !!profile.value?.is_configured)

  // =========================================================================
  // 方法
  // =========================================================================

  /** 从localStorage加载本地缓存 */
  function loadLocalCache() {
    try {
      const cached = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (cached) {
        preferences.value = { ...DEFAULT_PREFERENCES, ...JSON.parse(cached) }
      }
    } catch (e) {
      console.warn('读取本地偏好缓存失败:', e)
    }
  }

  /** 保存到localStorage */
  function saveLocalCache() {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(preferences.value))
    } catch (e) {
      console.warn('保存本地偏好缓存失败:', e)
    }
  }

  /** 从后端加载偏好 */
  async function fetchPreferences() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/preferences/')
      if (response.code === 0 && response.data) {
        preferences.value = { ...DEFAULT_PREFERENCES, ...response.data }
        saveLocalCache()
      }
    } catch (e) {
      console.error('加载偏好失败，使用本地缓存:', e)
      error.value = '加载偏好失败，使用本地缓存'
      loadLocalCache()
    } finally {
      loading.value = false
    }
  }

  /** 更新偏好 */
  async function updatePreferences(updateData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.put('/preferences/', updateData)
      if (response.code === 0 && response.data) {
        preferences.value = { ...preferences.value, ...response.data }
        saveLocalCache()
        return { success: true }
      }
      return { success: false, message: response.message }
    } catch (e) {
      console.error('更新偏好失败:', e)
      error.value = '更新偏好失败'
      return { success: false, message: '更新偏好失败' }
    } finally {
      loading.value = false
    }
  }

  /** 加载投资画像 */
  async function fetchProfile() {
    try {
      const response = await api.get('/preferences/profile')
      if (response.code === 0 && response.data) {
        profile.value = response.data
      }
    } catch (e) {
      console.error('加载画像失败:', e)
    }
  }

  /** 重置为默认值 */
  async function resetToDefaults() {
    return await updatePreferences(DEFAULT_PREFERENCES)
  }

  return {
    // 状态
    preferences,
    profile,
    loading,
    error,
    // 计算属性
    riskLabel,
    styleLabel,
    isConfigured,
    // 方法
    fetchPreferences,
    updatePreferences,
    fetchProfile,
    resetToDefaults,
    loadLocalCache,
  }
})
