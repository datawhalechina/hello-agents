<template>
  <a-config-provider :locale="zhCN" :theme="{ algorithm: configStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm }">
    <div class="app-container">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const configStore = useConfigStore()
const authStore = useAuthStore()

const syncAuth = () => {
  authStore.syncFromStorage()
  const isAuthPage = router.currentRoute.value.path.startsWith('/auth')
  if (!authStore.token && !isAuthPage) {
    router.replace('/auth/login')
  } else if (authStore.token && isAuthPage) {
    router.replace('/dashboard')
  }
}

onMounted(() => {
  window.addEventListener('storage', syncAuth)
  window.addEventListener('madf-auth-changed', syncAuth)
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', syncAuth)
  window.removeEventListener('madf-auth-changed', syncAuth)
})
</script>

<style>
html, body, #app, .app-container {
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden; /* Prevent global scrollbar */
}
</style>
