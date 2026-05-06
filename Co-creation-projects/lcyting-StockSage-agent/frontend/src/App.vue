<template>
  <div id="app-container">
    <el-container class="main-container">
      <!-- 侧边栏导航 -->
      <el-aside width="176px" class="sidebar">
        <div class="sidebar-logo">
          <el-icon :size="26"><TrendCharts /></el-icon>
          <span class="sidebar-logo-text">分析助手</span>
        </div>
        <!-- 不用 el-menu collapse：其在部分环境下会把除第一项外的图标槽位挤没；改用 router-link 稳定渲染 -->
        <nav class="sidebar-nav" aria-label="主导航">
          <router-link
            v-for="nav in sidebarNav"
            :key="nav.index"
            :to="nav.index"
            class="sidebar-link"
            :class="{ 'is-active': activeMenu === nav.index }"
            :title="nav.title"
            @mouseenter="prefetchRouteByNavPath(nav.index)"
          >
            <el-icon class="sidebar-nav-icon" :size="20">
              <component :is="nav.icon" />
            </el-icon>
            <span class="sidebar-link-text">{{ nav.title }}</span>
          </router-link>
        </nav>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header class="app-header">
          <div class="header-left">
            <h2 class="app-title">智能股票分析助手</h2>
          </div>
          <div class="header-right">
            <el-input
              v-model="searchText"
              placeholder="输入股票代码或名称..."
              class="header-search"
              clearable
            >
              <template #prefix>
                <el-icon><SearchIcon /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" circle @click="handleSearch">
              <el-icon><SearchIcon /></el-icon>
            </el-button>
          </div>
        </el-header>

        <el-main class="app-main">
          <!-- KeepAlive：已访问过的页面保留实例，切换回来时无需重新挂载/拉脚本 -->
          <!-- :key 绑定路由名，避免 KeepAlive + 异步组件时切换页面视图不更新 -->
          <router-view v-slot="{ Component }">
            <KeepAlive :include="cachedViews">
              <component
                :is="Component"
                v-if="Component"
                :key="route.name ?? route.path"
              />
            </KeepAlive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { prefetchRouteByNavPath } from '@/router/route-loaders.js'
import {
  TrendCharts,
  Odometer,
  DataAnalysis,
  Search as SearchIcon,
  Notebook,
  Money,
} from '@element-plus/icons-vue'

/** 与各页面 <script> export default { name } 一致，供 KeepAlive 命中缓存 */
const cachedViews = ['Dashboard', 'StockAnalysis', 'StockScreener', 'NewsCenter', 'Simulation']

/** 侧栏项：icon 为组件对象，供 :is 渲染（避免标签名与原生 HTML 冲突） */
const sidebarNav = [
  { index: '/dashboard', title: '仪表盘', icon: Odometer },
  { index: '/analysis', title: '股票分析', icon: DataAnalysis },
  { index: '/screener', title: '智能选股', icon: SearchIcon },
  { index: '/news', title: '新闻舆情', icon: Notebook },
  { index: '/simulation', title: '模拟交易', icon: Money },
]

const route = useRoute()
const router = useRouter()
const searchText = ref('')

/** 子路由（如 /analysis/600519）仍高亮对应菜单项 */
const activeMenu = computed(() => {
  const p = route.path
  if (p === '/' || p.startsWith('/dashboard')) return '/dashboard'
  if (p.startsWith('/analysis')) return '/analysis'
  if (p.startsWith('/screener')) return '/screener'
  if (p.startsWith('/news')) return '/news'
  if (p.startsWith('/simulation')) return '/simulation'
  return p
})

function handleSearch() {
  if (searchText.value.trim()) {
    router.push(`/analysis/${searchText.value.trim()}`)
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app, #app-container {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.main-container {
  height: 100%;
}

/* 侧边栏：图标 + 文字标题，固定宽度避免挤压 */
.sidebar {
  flex-shrink: 0;
  min-width: 176px;
  width: 176px !important;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  overflow-x: visible;
  overflow-y: auto;
}

.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 0 14px;
  color: #409eff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-logo-text {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 10px 8px;
  gap: 4px;
}

.sidebar-link {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  padding: 8px 12px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.72);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
  box-sizing: border-box;
}

.sidebar-link-text {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  white-space: nowrap;
}

.sidebar-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.sidebar-link.is-active {
  color: #409eff;
  background: rgba(64, 158, 255, 0.18);
}

.sidebar-nav-icon {
  display: inline-flex;
}

.sidebar-nav-icon svg {
  fill: currentColor;
}

/* 顶部栏 */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  height: 64px;
}

.app-title {
  font-size: 18px;
  color: #303133;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-search {
  width: 280px;
}

/* 主内容区：flex 子项默认可溢出隐藏，需 min-width:0 + 横向滚动，图表左边才不会被「吃掉」 */
.app-main {
  background: #f5f7fa;
  padding: 20px;
  min-width: 0;
  overflow-x: auto;
}
</style>
