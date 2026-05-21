<template>
  <div v-if="isStandalone" class="standalone-root">
    <router-view />
  </div>
  <a-layout v-else class="app-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      class="app-sider"
      :trigger="null"
      collapsible
      theme="dark"
      width="240"
    >
      <div class="logo">
        <span v-if="!collapsed">📚 知脉</span>
        <span v-else>📚</span>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="inline" @click="handleMenuClick">
        <a-menu-item key="search">
          <template #icon><RobotOutlined /></template>
          <span>文献搜索</span>
        </a-menu-item>
        <a-menu-item key="daily">
          <template #icon><CalendarOutlined /></template>
          <span>每日论文</span>
        </a-menu-item>
        <a-menu-item key="library">
          <template #icon><BookOutlined /></template>
          <span>我的文献库</span>
        </a-menu-item>
        <a-menu-item key="graph">
          <template #icon><ShareAltOutlined /></template>
          <span>知识图谱</span>
        </a-menu-item>
      </a-menu>
      <div v-if="!collapsed" class="app-sider__calendar">
        <ReadingCalendar />
      </div>
    </a-layout-sider>
    <a-layout class="app-main">
      <a-layout-header class="app-header">
        <h2 class="app-header__title">{{ pageTitle }}</h2>
      </a-layout-header>
      <a-layout-content class="app-content" :class="{ 'app-content--no-scroll': contentNoScroll }">
        <div class="app-content__inner" :class="{ 'app-content__inner--no-scroll': contentNoScroll }">
          <router-view v-slot="{ Component }">
            <keep-alive include="SearchAgent,DailyArxiv">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ReadingCalendar from '@/components/ReadingCalendar.vue'
import {
  RobotOutlined,
  CalendarOutlined,
  BookOutlined,
  ShareAltOutlined,
} from '@ant-design/icons-vue'
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref<string[]>(['search'])
const isStandalone = computed(() => {
  const n = String(route.name || '').toLowerCase()
  return n === 'library-read' && String(route.query?.standalone || '') === '1'
})
const contentNoScroll = computed(() => {
  const n = String(route.name || '').toLowerCase()
  return n === 'search'
})
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    search: '文献搜索',
    daily: '每日论文',
    library: '我的文献库',
    'library-read': '文献阅读',
    graph: '知识图谱',
  }
  const name = (route.name as string)?.toLowerCase() || ''
  return titles[name] || '知脉'
})
const handleMenuClick = ({ key }: { key: string }) => {
  router.push(`/${key}`)
}
watch(
  () => route.name,
  (name) => {
    const n = String(name || '').toLowerCase()
    if (n === 'library-read') selectedKeys.value = ['library']
    else if (n) selectedKeys.value = [n]
  },
  { immediate: true }
)
</script>
<style scoped>
.standalone-root {
  height: 100vh;
  width: 100vw;
  min-height: 100vh;
  background: #fff;
}
.app-layout {
  height: 100vh;
  overflow: hidden;
}
.app-sider {
  height: 100vh;
  overflow: hidden;
  position: sticky;
  top: 0;
  left: 0;
}
.app-sider :deep(.ant-layout-sider-children) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.app-sider :deep(.ant-menu) {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.app-sider__calendar {
  flex: 0 0 auto;
  padding-top: 10px;
}
.app-main {
  min-height: 0;
  overflow: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.app-header {
  background: #fff;
  padding: 0 24px;
  flex: 0 0 auto;
}
.app-header__title {
  margin: 0;
  font-size: 18px;
}
.app-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.app-content__inner {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  flex: 1 1 auto;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.app-content.app-content--no-scroll {
  overflow: hidden;
  padding: 0;
  flex: 1 1 0;
  min-height: 0;
}
.app-content__inner.app-content__inner--no-scroll {
  flex: 1 1 0;
  min-height: 0;
  height: auto;
  padding: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
</style>