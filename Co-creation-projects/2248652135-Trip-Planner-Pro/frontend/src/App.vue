<template>
  <div id="app">
    <a-layout style="min-height: 100vh">
      <a-layout-header style="background: #001529; padding: 0 50px; display: flex; align-items: center; justify-content: space-between;">
        <div style="color: white; font-size: 24px; font-weight: bold; cursor: pointer;" @click="goHome">
          🌍 HelloAgents智能旅行助手
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <a-button v-if="isLoggedIn" type="text" style="color: white;" @click="goHistory">
            📋 历史记录
          </a-button>
          <a-button v-if="isLoggedIn" type="text" style="color: white;" @click="goChat">
            💬 AI对话
          </a-button>
          <span v-if="isLoggedIn" style="color: rgba(255,255,255,0.65);">👤 {{ username }}</span>
          <a-button v-if="!isLoggedIn" type="primary" ghost @click="goLogin">登录</a-button>
          <a-button v-else type="text" style="color: rgba(255,255,255,0.65);" @click="handleLogout">退出</a-button>
        </div>
      </a-layout-header>
      <a-layout-content style="padding: 24px">
        <router-view />
      </a-layout-content>
      <a-layout-footer style="text-align: center">
        HelloAgents智能旅行助手 ©2025 基于HelloAgents框架
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { apiBaseUrl } from '@/services/api'

const router = useRouter()
const isLoggedIn = ref(false)
const username = ref('')

async function checkAuth() {
  // 先读 localStorage 缓存（避免每次路由切换都请求）
  const cachedUser = localStorage.getItem('auth_username')
  isLoggedIn.value = !!cachedUser
  username.value = cachedUser || ''

  // 异步验证：确认 cookie 真的有效
  try {
    const res = await fetch(`${apiBaseUrl}/api/auth/profile`, {
      credentials: 'include',
    })
    if (res.ok) {
      const data = await res.json()
      isLoggedIn.value = true
      username.value = data.username
      localStorage.setItem('auth_username', data.username)
    } else {
      isLoggedIn.value = false
      username.value = ''
      localStorage.removeItem('auth_username')
    }
  } catch {
    // 后端未启动时不改变状态
  }
}

// 每次路由切换时重新检查
router.afterEach(() => {
  checkAuth()
})

function goHome() {
  router.push('/')
}

function goLogin() {
  router.push('/login')
}

function goHistory() {
  if (!isLoggedIn.value) {
    message.warning('请先登录')
    router.push('/login')
    return
  }
  router.push('/history')
}

function goChat() {
  if (!isLoggedIn.value) {
    message.warning('请先登录')
    router.push('/login')
    return
  }
  router.push('/chat')
}

async function handleLogout() {
  try {
    await fetch(`${apiBaseUrl}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch {}
  localStorage.removeItem('auth_username')
  isLoggedIn.value = false
  username.value = ''
  message.success('已退出登录')
  router.push('/')
}

onMounted(checkAuth)
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>
