import { createRouter, createWebHistory } from 'vue-router'
import {
  loadDashboardView,
  loadStockAnalysisView,
  loadStockScreenerView,
  loadNewsCenterView,
  loadSimulationView,
  loaderForPath,
  prefetchRouteChunksIdle,
} from './route-loaders.js'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: loadDashboardView,
    meta: { title: '仪表盘' },
  },
  {
    path: '/analysis/:code?',
    name: 'StockAnalysis',
    component: loadStockAnalysisView,
    meta: { title: '股票分析' },
  },
  {
    path: '/screener',
    name: 'StockScreener',
    component: loadStockScreenerView,
    meta: { title: '智能选股' },
  },
  {
    path: '/news',
    name: 'NewsCenter',
    component: loadNewsCenterView,
    meta: { title: '新闻舆情' },
  },
  {
    path: '/simulation',
    name: 'Simulation',
    component: loadSimulationView,
    meta: { title: '模拟交易' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.isReady().then(() => {
  prefetchRouteChunksIdle(loaderForPath(router.currentRoute.value.path))
})

export default router
