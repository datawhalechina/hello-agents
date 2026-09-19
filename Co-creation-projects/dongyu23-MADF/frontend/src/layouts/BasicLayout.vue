<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      theme="light"
      breakpoint="lg"
      :width="220"
      class="sider-layout"
    >
      <div class="logo">
        <span v-if="!collapsed" class="logo-text">MADF 论坛</span>
        <span v-else class="logo-text">M</span>
      </div>
      <a-menu :selectedKeys="selectedKeys" theme="light" mode="inline">
        <a-menu-item key="dashboard" @click="navigateTo('/dashboard')">
            <dashboard-outlined />
            <span>概览</span>
        </a-menu-item>
        
        <a-menu-item key="personas" @click="navigateTo('/personas')">
            <team-outlined />
            <span>智能体工坊</span>
        </a-menu-item>
        
        <a-menu-item key="forums" @click="navigateTo('/forums')">
            <comment-outlined />
            <span>圆桌论坛</span>
        </a-menu-item>

        <a-menu-divider />
        
        <a-menu-item key="logout" @click="handleLogout">
          <logout-outlined />
          <span>退出登录</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    
    <a-layout class="site-layout">
      <!-- Header removed -->
      
      <a-layout-content style="margin: 0; padding: 0; height: 100vh; overflow: hidden;">
        <div :style="{ padding: '0', background: '#fff', height: '100%' }">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DashboardOutlined,
  TeamOutlined,
  CommentOutlined,
  LogoutOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const handleLogout = async () => {
  await authStore.logout()
}

const navigateTo = (path: string) => {
    router.push(path)
}

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['forums']
  return []
})
</script>

<style scoped>
.logo {
  height: 32px;
  margin: 16px;
  background: rgba(24, 144, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  white-space: nowrap;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: #1890ff;
}

.sider-layout {
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  z-index: 10;
  height: 100vh;
  overflow-y: auto;
}

/* Ensure the layout takes full width */
.site-layout {
  height: 100vh;
  overflow: hidden;
}
</style>
