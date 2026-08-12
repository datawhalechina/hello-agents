<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { Menu, ConfigProvider, theme } from 'ant-design-vue'
import { MessageOutlined, SettingOutlined, HistoryOutlined, BookOutlined } from '@ant-design/icons-vue'
import LobsterIcon from '@/assets/lobster.svg'

const route = useRoute()

// 龙虾红主题配置
const customTheme = {
  token: {
    colorPrimary: '#ff5c5c',
    colorPrimaryHover: '#ff7070',
    colorPrimaryActive: '#e64a4a',
    colorPrimaryBg: 'rgba(255, 92, 92, 0.1)',
    colorPrimaryBgHover: 'rgba(255, 92, 92, 0.2)',
  },
}
</script>

<template>
  <ConfigProvider :theme="{ token: customTheme.token }">
    <div class="app-container">
      <aside class="sidebar">
        <div class="logo">
          <img :src="LobsterIcon" alt="HelloClaw" class="logo-icon" />
          <span class="logo-text">HelloClaw</span>
        </div>
        <Menu
          mode="inline"
          :selected-keys="[route.name as string]"
          class="sidebar-menu"
        >
          <Menu.Item key="chat">
            <RouterLink to="/">
              <MessageOutlined />
              <span>聊天</span>
            </RouterLink>
          </Menu.Item>
          <Menu.Item key="sessions">
            <RouterLink to="/sessions">
              <HistoryOutlined />
              <span>会话</span>
            </RouterLink>
          </Menu.Item>
          <Menu.Item key="memory">
            <RouterLink to="/memory">
              <BookOutlined />
              <span>记忆</span>
            </RouterLink>
          </Menu.Item>
          <Menu.Item key="config">
            <RouterLink to="/config">
              <SettingOutlined />
              <span>配置</span>
            </RouterLink>
          </Menu.Item>
        </Menu>
      </aside>

      <main class="main-content">
        <RouterView />
      </main>
    </div>
  </ConfigProvider>
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  background-color: #fff;
  border-right: 1px solid #f0f0f0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.logo {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.logo-icon {
  width: 36px;
  height: 36px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding-top: 8px;
}

.main-content {
  flex: 1;
  background-color: #f5f5f5;
  overflow: auto;
  height: 100vh;
}
</style>
