<template>
  <div v-if="!authStore.isLoggedIn" class="login-view">
    <router-view />
  </div>
  <div v-else class="app-layout" :data-theme="themeStore.theme">
    <nav class="app-nav">
      <div class="nav-brand">{{ langStore.t('nav.brand') }}</div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">{{ langStore.t('nav.chat') }}</router-link>
        <router-link to="/learning" class="nav-link">{{ langStore.t('nav.learning') }}</router-link>
        <router-link to="/dashboard" class="nav-link">{{ langStore.t('nav.dashboard') }}</router-link>
        <router-link to="/orchestration" class="nav-link">{{ langStore.t('nav.orchestration') }}</router-link>
      </div>
      <div class="nav-user">
        <button class="icon-btn" @click="showSettings = true" title="LLM 配置">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
        <button class="theme-toggle" @click="themeStore.toggleTheme" :title="themeStore.theme === 'dark' ? langStore.t('theme.light') : langStore.t('theme.dark')">
          {{ themeStore.theme === 'dark' ? '☀️' : '🌙' }}
        </button>
        <button class="lang-toggle" @click="langStore.toggleLang" :title="langStore.t('nav.switchLang')">
          {{ langStore.lang === 'zh' ? 'EN' : '中' }}
        </button>
        <span class="user-id">{{ authStore.userId }}</span>
        <button class="logout-btn" @click="handleLogout" :title="langStore.t('nav.logout')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </nav>
    <router-view v-slot="{ Component }">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>
    <SettingsModal :visible="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from './stores/authStore'
import { useThemeStore } from './stores/themeStore'
import { useLangStore } from './stores/langStore'
import { useRouter } from 'vue-router'
import SettingsModal from './components/SettingsModal.vue'

const showSettings = ref(false)
const authStore = useAuthStore()
const themeStore = useThemeStore()
const langStore = useLangStore()
const router = useRouter()

// Initialize theme on app start
themeStore.init()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-nav {
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 56px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.nav-brand {
  font-size: 18px;
  font-weight: 600;
  margin-right: 32px;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.nav-link.router-link-active {
  background: rgba(255, 255, 255, 0.25);
  color: white;
  font-weight: 500;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.user-id {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.15);
  padding: 4px 12px;
  border-radius: 12px;
}

.logout-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.lang-toggle {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  transition: background 0.2s;
  letter-spacing: 0.5px;
}

.lang-toggle:hover {
  background: rgba(255, 255, 255, 0.3);
}

.icon-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
  color: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.theme-toggle {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
}

.login-view {
  height: 100vh;
}
</style>
