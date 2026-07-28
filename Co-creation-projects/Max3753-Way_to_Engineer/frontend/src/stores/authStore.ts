import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'currentUserId'

export const useAuthStore = defineStore('auth', () => {
  const userId = ref<string>(localStorage.getItem(STORAGE_KEY) || '')

  const isLoggedIn = computed(() => userId.value.length > 0)

  const login = (id: string) => {
    userId.value = id
    localStorage.setItem(STORAGE_KEY, id)
  }

  const logout = () => {
    userId.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  const getUserId = () => userId.value

  return {
    userId,
    isLoggedIn,
    login,
    logout,
    getUserId
  }
})
