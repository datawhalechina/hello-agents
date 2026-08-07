/**
 * 自选股：调用后端 POST /watchlist，并通知仪表盘清理本地快照
 */
import { ElMessage } from 'element-plus'
import api from '@/api'

/** 与 Dashboard.vue 中 localStorage 键一致，便于任意页面加入自选后失效快照 */
/** v2：快照内含资讯 url 等字段；升级键名使旧版 exe/浏览器缓存一次性失效，避免长期沿用无原文链接的快照 */
export const DASHBOARD_SNAPSHOT_LS_KEY = 'stock_analyzer_dashboard_snapshot_v2'

/**
 * 自选变更待同步：仪表盘 KeepAlive/未挂载时可能收不到 CustomEvent，
 * 用户切回仪表盘时根据此标记强制拉自选（见 Dashboard hydrateDashboard）。
 */
export const WATCHLIST_REFRESH_PENDING_LS_KEY =
  'stock_analyzer_watchlist_refresh_pending_v1'

export const WATCHLIST_CHANGED_EVENT = 'stock-analyzer-watchlist-changed'

function clearDashboardSnapshotGlobal() {
  try {
    localStorage.removeItem(DASHBOARD_SNAPSHOT_LS_KEY)
  } catch {
    /* ignore */
  }
}

/** 标记「进入仪表盘时需刷新自选」；由 consumeWatchlistRefreshPending 读后清除 */
export function setWatchlistRefreshPending() {
  try {
    localStorage.setItem(WATCHLIST_REFRESH_PENDING_LS_KEY, '1')
  } catch {
    /* ignore */
  }
}

/** @returns {boolean} 是否曾在其它页加入/变更自选且尚未在仪表盘消费 */
export function consumeWatchlistRefreshPending() {
  try {
    const v = localStorage.getItem(WATCHLIST_REFRESH_PENDING_LS_KEY)
    if (v === '1') {
      localStorage.removeItem(WATCHLIST_REFRESH_PENDING_LS_KEY)
      return true
    }
  } catch {
    /* ignore */
  }
  return false
}

export function notifyWatchlistChanged() {
  clearDashboardSnapshotGlobal()
  setWatchlistRefreshPending()
  try {
    window.dispatchEvent(new CustomEvent(WATCHLIST_CHANGED_EVENT))
  } catch {
    /* ignore */
  }
}

/**
 * @param {string} stockInput 股票代码或名称
 * @param {{ silent?: boolean }} options
 */
export async function addStockToWatchlist(stockInput, options = {}) {
  const { silent = false } = options
  const s = String(stockInput ?? '').trim()
  if (!s) {
    if (!silent) ElMessage.warning('请先选择有效的股票代码或名称')
    return { ok: false }
  }
  try {
    const res = await api.post('/watchlist/', { stock: s })
    if (res.code === 0) {
      if (!silent) ElMessage.success(res.message || '已加入自选股')
      notifyWatchlistChanged()
      return { ok: true, message: res.message }
    }
    if (!silent) ElMessage.error(res.message || '添加自选股失败')
    return { ok: false, message: res.message }
  } catch (e) {
    if (!silent) ElMessage.error('添加失败：' + (e.message || '网络错误'))
    return { ok: false }
  }
}

/** 从选股结果行解析代码（优先 6 位数字），供加自选 / 跳转分析复用 */
export function pickScreenerStockCode(row) {
  if (!row || typeof row !== 'object') return ''
  const raw =
    row['股票代码'] ??
    row['代码'] ??
    row['证券代码'] ??
    ''
  const s = String(raw).trim()
  const m = s.match(/\d{6}/)
  return m ? m[0] : s
}
