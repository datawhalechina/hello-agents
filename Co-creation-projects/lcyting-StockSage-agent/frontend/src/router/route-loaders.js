/**
 * 路由页面分包加载 — 独立文件，避免与 router 实例互相引用形成循环依赖
 */

export function loadDashboardView() {
  return import('@/views/Dashboard.vue')
}
export function loadStockAnalysisView() {
  return import('@/views/StockAnalysis.vue')
}
export function loadStockScreenerView() {
  return import('@/views/StockScreener.vue')
}
export function loadNewsCenterView() {
  return import('@/views/NewsCenter.vue')
}
export function loadSimulationView() {
  return import('@/views/Simulation.vue')
}

export const ALL_ROUTE_LOADERS = [
  loadDashboardView,
  loadStockAnalysisView,
  loadStockScreenerView,
  loadNewsCenterView,
  loadSimulationView,
]

export function loaderForPath(path) {
  if (path === '/' || path.startsWith('/dashboard')) return loadDashboardView
  if (path.startsWith('/analysis')) return loadStockAnalysisView
  if (path.startsWith('/screener')) return loadStockScreenerView
  if (path.startsWith('/news')) return loadNewsCenterView
  if (path.startsWith('/simulation')) return loadSimulationView
  return null
}

export function prefetchRouteChunksIdle(excludeLoader) {
  const loaders = excludeLoader
    ? ALL_ROUTE_LOADERS.filter((fn) => fn !== excludeLoader)
    : [...ALL_ROUTE_LOADERS]

  const run = () => {
    loaders.forEach((loader) => {
      loader().catch(() => {})
    })
  }

  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(run, { timeout: 2500 })
  } else {
    setTimeout(run, 280)
  }
}

export function prefetchRouteByNavPath(navPath) {
  const map = {
    '/dashboard': loadDashboardView,
    '/analysis': loadStockAnalysisView,
    '/screener': loadStockScreenerView,
    '/news': loadNewsCenterView,
    '/simulation': loadSimulationView,
  }
  const loader = map[navPath]
  if (loader) loader().catch(() => {})
}
