<template>
  <div class="dashboard-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>仪表盘</h2>
      <el-text type="info">市场概览 · 自选股动态 · 热点快讯</el-text>
    </div>

    <!-- 市场概览 — 指数卡片 -->
    <el-row :gutter="16" class="index-row" v-loading="indexLoading">
      <el-col :span="6" v-for="item in indices" :key="item.name">
        <el-card shadow="hover" class="index-card">
          <div class="index-name">{{ item.name }}</div>
          <div class="index-value">{{ item.price ?? '--' }}</div>
          <div
            v-if="Number.isFinite(item.change)"
            :class="['index-change', item.change >= 0 ? 'up' : 'down']"
          >
            <el-icon v-if="item.change >= 0" class="change-icon"><CaretTop /></el-icon>
            <el-icon v-else class="change-icon"><CaretBottom /></el-icon>
            {{ item.change >= 0 ? '+' : '' }}{{ item.change }}
            <span class="change-unit">%</span>
          </div>
          <el-text v-else-if="indexLoading" type="info" size="small">加载中...</el-text>
          <el-text v-else type="info" size="small">--</el-text>
        </el-card>
      </el-col>
    </el-row>

    <!-- 自选股 + 热点快讯 双栏 -->
    <el-row :gutter="16" class="content-row">
      <!-- 自选股动态 -->
      <el-col :span="16">
        <el-card shadow="hover" class="watchlist-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">自选股动态</span>
              <el-button type="primary" link @click="$router.push('/analysis')">
                查看更多 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>

          <div v-loading="watchlistLoading">
            <!-- 有自选股时展示表格 -->
            <el-table
              v-if="watchlist.length > 0"
              :data="watchlist"
              stripe
              style="width: 100%"
              @row-click="(row) => $router.push(`/analysis/${row.code}`)"
            >
              <el-table-column prop="name" label="股票名称" width="140" />
              <el-table-column prop="code" label="代码" width="100" />
              <el-table-column prop="price" label="最新价" width="100" />
              <el-table-column label="涨跌幅" width="100">
                <template #default="{ row }">
                  <span :class="parseFloat(row.change) >= 0 ? 'text-up' : 'text-down'">
                    {{ row.change ?? '--' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    link
                    size="small"
                    @click.stop="handleRemoveWatch(row)"
                  >
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 无自选股时展示空状态 -->
            <el-empty
              v-else-if="!watchlistLoading"
              description="暂无自选股"
              :image-size="80"
            >
              <el-button type="primary" @click="$router.push('/screener')">
                去选股
              </el-button>
            </el-empty>
          </div>
        </el-card>
      </el-col>

      <!-- 热点快讯 -->
      <el-col :span="8">
        <el-card shadow="hover" class="news-card">
          <template #header>
            <div class="card-header">
              <div class="card-title-row">
                <span class="card-title">热点快讯</span>
                <el-text size="small" type="info">点击条目查看全文</el-text>
              </div>
              <el-tag size="small" type="danger">实时</el-tag>
            </div>
          </template>

          <div v-loading="newsLoading" class="news-list">
            <el-empty
              v-if="hotNews.length === 0 && !newsLoading"
              description="暂无热门资讯"
              :image-size="60"
            />
            <div
              v-for="(item, idx) in hotNews"
              :key="idx"
              class="news-item"
              role="button"
              tabindex="0"
              @click="openNewsDetail(item)"
              @keyup.enter="openNewsDetail(item)"
            >
              <div class="news-title">{{ item.title }}</div>
              <div class="news-meta">
                <el-tag
                  size="small"
                  :type="item.info_type === 'REPORT' ? 'warning' : item.info_type === 'ANNOUNCEMENT' ? '' : 'success'"
                >
                  {{ item.info_type_cn || item.info_type }}
                </el-tag>
                <span class="news-date">{{ item.date }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 热点快讯：点击查看全文 / 原文链接 -->
    <NewsDetailDrawer v-model="newsDrawerVisible" :item="newsDetailItem" />
  </div>
</template>

<script>
/** KeepAlive 按组件 name 缓存，须与 App.vue 中 cachedViews 一致 */
export default { name: 'Dashboard' }
</script>

<script setup>
/**
 * 仪表盘页面
 *
 * 展示市场概览指数卡片、自选股动态表格、热点快讯列表。
 * 数据来源：后端 /api/v1/market, /api/v1/watchlist, /api/v1/news
 */
import { ref, onMounted, onActivated, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import NewsDetailDrawer from '@/components/NewsDetailDrawer.vue'
import {
  WATCHLIST_CHANGED_EVENT,
  DASHBOARD_SNAPSHOT_LS_KEY,
  consumeWatchlistRefreshPending,
} from '@/utils/watchlist'

const router = useRouter()

/** 关注的四大指数 */
const INDEX_LIST = ['上证指数', '深证成指', '创业板指', '沪深300']

// =========================================================================
// 响应式状态
// =========================================================================
const indices = ref(INDEX_LIST.map(name => ({ name, price: null, change: null })))
const indexLoading = ref(false)

const watchlist = ref([])
const watchlistLoading = ref(false)

const hotNews = ref([])
const newsLoading = ref(false)

/** 资讯全文抽屉 */
const newsDrawerVisible = ref(false)
const newsDetailItem = ref(null)

function openNewsDetail(item) {
  newsDetailItem.value = item
  newsDrawerVisible.value = true
}

/** 默认 TTL 与后端 MX_CACHE_TTL_SECONDS（秒）一致 */
const _ttlMs = Number(import.meta.env.VITE_DASHBOARD_CACHE_MS)
const DASHBOARD_CACHE_TTL_MS =
  Number.isFinite(_ttlMs) && _ttlMs > 0 ? _ttlMs : 10 * 60 * 1000

function readDashboardSnapshot() {
  try {
    const raw = localStorage.getItem(DASHBOARD_SNAPSHOT_LS_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (!o || typeof o.ts !== 'number' || !Array.isArray(o.indices)) return null
    return o
  } catch {
    return null
  }
}

function writeDashboardSnapshot() {
  try {
    localStorage.setItem(
      DASHBOARD_SNAPSHOT_LS_KEY,
      JSON.stringify({
        ts: Date.now(),
        indices: indices.value,
        watchlist: watchlist.value,
        hotNews: hotNews.value,
      }),
    )
  } catch (e) {
    console.warn('仪表盘缓存写入失败:', e)
  }
}

function clearDashboardSnapshot() {
  try {
    localStorage.removeItem(DASHBOARD_SNAPSHOT_LS_KEY)
  } catch {
    /* ignore */
  }
}

function applyDashboardSnapshot(o) {
  indices.value = o.indices
  watchlist.value = Array.isArray(o.watchlist) ? o.watchlist : []
  hotNews.value = Array.isArray(o.hotNews) ? o.hotNews : []
}

// =========================================================================
// 数据解析工具函数
// =========================================================================

/**
 * 将表格单元格解析为数值（涨跌幅常见："+1.23%"、"-0.5"、"--"、全角符号）
 * 无法解析时返回 null，避免出现 NaN%
 */
function parseNumericCell(val) {
  if (val === null || val === undefined) return null
  if (typeof val === 'number') {
    return Number.isFinite(val) ? val : null
  }
  const raw = String(val).trim()
  if (!raw || raw === '--' || raw === '—' || raw === '-' || raw === '暂无') return null
  const cleaned = raw
    .replace(/[%％]/g, '')
    .replace(/,/g, '')
    .replace(/＋/g, '+')
    .replace(/——|--|−|－/g, '-')
  const m = cleaned.match(/[-+]?[\d.]+(?:e[-+]?\d+)?/i)
  if (!m) return null
  const num = parseFloat(m[0])
  return Number.isFinite(num) ? num : null
}

/** 宽表：按列下标取单元格（mx_data 的 rows 为对象数组，须用 fieldnames 作 key） */
function cellAt(names, row, colIdx) {
  if (colIdx < 0 || row == null) return null
  if (Array.isArray(row)) return row[colIdx]
  const key = names[colIdx]
  return key != null ? row[key] : null
}

/** 根据表头与单元格内容推断「涨跌幅」列下标 */
function findIndexChangeColumn(fieldnames, row) {
  const names = fieldnames || []
  let idx = names.findIndex(f =>
    /涨跌幅|涨跌幅度|当日涨幅|涨跌幅幅度|日涨跌幅/.test(String(f))
  )
  if (idx < 0) {
    idx = names.findIndex(f => /^涨幅$|涨跌幅度|变动率/.test(String(f)))
  }
  if (idx >= 0) return idx
  // 兜底：找首个带 % 且能解析为数的列
  for (let j = 0; j < names.length; j++) {
    const v = cellAt(names, row, j)
    if (v != null && /%/.test(String(v)) && parseNumericCell(v) !== null) return j
  }
  return -1
}

/**
 * 长表：mx_data 在「单行日期」模式下 fieldnames 恰为两列，每行 { 列0: 指标名, 列1: 数值 }
 */
function parseIndexLongTable(names, rows) {
  if (!names || names.length !== 2 || rows.length < 1) return null
  const labelKey = names[0]
  const valueKey = names[1]
  if (!labelKey || !valueKey) return null

  let price = null
  let change = null
  for (const r of rows) {
    const label = String(r[labelKey] ?? '').trim()
    const rawVal = r[valueKey]
    if (/涨跌幅|涨跌幅度|当日涨幅|涨跌|涨幅|变动率/.test(label)) {
      const n = parseNumericCell(rawVal)
      if (n !== null) change = n
    } else if (
      /点位|最新点|收盘点|指数点位|收盘价|最新价|现价|收盘|价格|最新|上证|深证|成指|沪深300|创业板指/.test(
        label
      )
    ) {
      if (price == null && rawVal != null && String(rawVal).trim() !== '') price = rawVal
    }
  }
  if (price == null && change == null) return null
  return { price, change }
}

/** 单张 mx sheet 解析指数点位与涨跌幅（与后端 market_service 列名兜底蕴思路对齐） */
function parseIndexFromSingleTable(table) {
  try {
    const names = table.fieldnames || table.fieldNames || []
    const rows = table.rows || []
    if (rows.length === 0) return null

    const dateColIdx = names.findIndex(f => /日期|时间|^date$/i.test(String(f)))
    const dataRow =
      dateColIdx >= 0 && rows.length > 1 ? rows[rows.length - 1] : rows[0]

    const priceColRe =
      /点位|最新点|收盘点|指数点位|收盘价|最新价|现价|收盘|价格|数值|报价|行情/
    // 宽表：一行多指标列
    const priceIdx = names.findIndex(f => priceColRe.test(String(f)))
    const changeIdx = findIndexChangeColumn(names, dataRow)
    const rawPrice = priceIdx >= 0 ? cellAt(names, dataRow, priceIdx) : null
    const rawChange = changeIdx >= 0 ? cellAt(names, dataRow, changeIdx) : null
    if (
      (rawPrice != null && rawPrice !== '') ||
      (rawChange != null && String(rawChange).trim() !== '')
    ) {
      return {
        price: rawPrice != null && rawPrice !== '' ? rawPrice : null,
        change: changeIdx >= 0 ? parseNumericCell(rawChange) : null,
      }
    }

    // 长表：多行「指标名 → 数值」
    const longParsed = parseIndexLongTable(names, rows)
    if (longParsed) return longParsed

    // 兼容旧版：row 为数组
    if (Array.isArray(dataRow)) {
      const pIdx = names.findIndex(f => priceColRe.test(String(f)))
      const cIdx = findIndexChangeColumn(names, dataRow)
      return {
        price: pIdx >= 0 ? dataRow[pIdx] : null,
        change: cIdx >= 0 ? parseNumericCell(dataRow[cIdx]) : null,
      }
    }

    return null
  } catch {
    return null
  }
}

/**
 * 从 mx-data 表格数据中提取指数行情值
 * API: tables[].fieldnames + rows（rows 为对象数组；妙想常返回多 sheet，须遍历合并）
 */
function parseIndexData(data) {
  try {
    if (!data || !data.success) return null

    let price =
      data.display_price != null && String(data.display_price).trim() !== ''
        ? data.display_price
        : null
    let change = null
    const rawCh = data.display_change_pct
    if (typeof rawCh === 'number' && Number.isFinite(rawCh)) {
      change = rawCh
    } else if (rawCh != null && String(rawCh).trim() !== '') {
      change = parseNumericCell(rawCh)
    }

    if (data.tables && data.tables.length > 0) {
      for (const table of data.tables) {
        const parsed = parseIndexFromSingleTable(table)
        if (!parsed) continue
        if (
          (price == null || String(price).trim() === '') &&
          parsed.price != null &&
          String(parsed.price).trim() !== ''
        ) {
          price = parsed.price
        }
        if (
          (change == null || !Number.isFinite(change)) &&
          parsed.change != null &&
          Number.isFinite(parsed.change)
        ) {
          change = parsed.change
        }
        if (
          price != null &&
          String(price).trim() !== '' &&
          change != null &&
          Number.isFinite(change)
        ) {
          break
        }
      }
    }

    if (
      (price == null || String(price).trim() === '') &&
      (change == null || !Number.isFinite(change))
    ) {
      return null
    }
    return { price, change }
  } catch {
    return null
  }
}

/**
 * 从 mx-data 表格数据中提取个股行情
 * 与指数解析对齐：多行且含日期列时取最后一行（通常为最新）；涨跌幅列用 findIndexChangeColumn 兜底
 */
function parseStockQuote(data) {
  try {
    if (!data || !data.success || !data.tables || data.tables.length === 0) return null
    const table = data.tables[0]
    const names = table.fieldnames || table.fieldNames || []
    const rows = table.rows || []
    if (rows.length === 0) return null

    const dateColIdx = names.findIndex(f => /日期|时间|^date$/i.test(String(f)))
    const dataRow =
      dateColIdx >= 0 && rows.length > 1 ? rows[rows.length - 1] : rows[0]

    const nameIdx = names.findIndex(f => /名称|简称|股票/.test(String(f)))
    const priceIdx = names.findIndex(f =>
      /点位|最新点|收盘点|收盘价|最新价|现价|收盘|价格|报价|数值/.test(String(f))
    )
    const changeIdx = findIndexChangeColumn(names, dataRow)

    const rawPrice = priceIdx >= 0 ? cellAt(names, dataRow, priceIdx) : null
    const rawChange = changeIdx >= 0 ? cellAt(names, dataRow, changeIdx) : null
    const parsedChange = changeIdx >= 0 ? parseNumericCell(rawChange) : null

    if (
      (rawPrice != null && rawPrice !== '') ||
      (parsedChange != null && Number.isFinite(parsedChange))
    ) {
      return {
        name: nameIdx >= 0 ? cellAt(names, dataRow, nameIdx) : null,
        price: rawPrice != null && rawPrice !== '' ? rawPrice : null,
        change: parsedChange,
      }
    }

    // 长表：两列指标名→数值
    if (!Array.isArray(dataRow) && names.length === 2) {
      const long = parseIndexLongTable(names, rows)
      if (long && (long.price != null || long.change != null)) {
        const row0 = rows[0]
        return {
          name: nameIdx >= 0 && row0 && !Array.isArray(row0) ? cellAt(names, row0, nameIdx) : null,
          price: long.price,
          change: long.change != null ? long.change : null,
        }
      }
    }

    const longParsed = parseIndexLongTable(names, rows)
    if (longParsed && (longParsed.price != null || longParsed.change != null)) {
      const row0 = rows[0]
      return {
        name:
          nameIdx >= 0 && row0 && !Array.isArray(row0) ? cellAt(names, row0, nameIdx) : null,
        price: longParsed.price,
        change: longParsed.change != null ? longParsed.change : null,
      }
    }

    if (Array.isArray(dataRow)) {
      const pIdx = names.findIndex(f =>
        /最新价|现价|收盘|价格/.test(String(f))
      )
      const cIdx = findIndexChangeColumn(names, dataRow)
      return {
        name: nameIdx >= 0 ? dataRow[nameIdx] : null,
        price: pIdx >= 0 ? dataRow[pIdx] : null,
        change: cIdx >= 0 ? parseNumericCell(dataRow[cIdx]) : null,
      }
    }

    return null
  } catch {
    return null
  }
}

/** 自选列表 mx_zixuan 返回的涨跌幅字段可能是数字或带 % 的字符串 */
function parseWatchlistChangePct(raw) {
  if (raw == null || raw === '') return null
  const n = parseNumericCell(raw)
  return n != null && Number.isFinite(n) ? n : null
}

// =========================================================================
// 数据加载
// =========================================================================

/** 加载指数行情 */
async function loadIndices() {
  indexLoading.value = true
  try {
    const promises = INDEX_LIST.map(name =>
      api
        .get('/market/index', { params: { name } })
        .then((res) => {
          if (!res || res.code !== 0 || res.data == null) return null
          return res.data
        })
        .catch(() => null)
    )
    const results = await Promise.all(promises)
    indices.value = INDEX_LIST.map((name, i) => {
      const parsed = parseIndexData(results[i])
      return {
        name,
        price: parsed?.price ?? null,
        change: parsed?.change ?? null,
      }
    })
  } catch (e) {
    console.error('加载指数行情失败:', e)
  } finally {
    indexLoading.value = false
  }
}

/** 加载自选股列表 */
async function loadWatchlist() {
  watchlistLoading.value = true
  try {
    const res = await api.get('/watchlist/')
    if (res.code === 0 && res.data?.stocks) {
      watchlist.value = res.data.stocks.map(stock => {
        const zPrice =
          stock.price != null && String(stock.price).trim() !== '' ? stock.price : null
        const zChange = parseWatchlistChangePct(stock.change_pct)
        return {
          code: stock.code || stock.name,
          name: stock.name || stock.code || '--',
          price: zPrice ?? '--',
          change: zChange ?? '--',
        }
      })
    }
  } catch (e) {
    console.error('加载自选股失败:', e)
  } finally {
    watchlistLoading.value = false
  }
}

/** 加载热点快讯 */
async function loadHotNews() {
  newsLoading.value = true
  try {
    const res = await api.get('/news/hot')
    if (res.code === 0 && res.data?.items) {
      // 只取前8条
      hotNews.value = res.data.items.slice(0, 8)
    }
  } catch (e) {
    console.error('加载热点快讯失败:', e)
  } finally {
    newsLoading.value = false
  }
}

/** 移除自选股 */
async function handleRemoveWatch(row) {
  try {
    await ElMessageBox.confirm(
      `确定要从自选股中移除 ${row.name}（${row.code}）吗？`,
      '移除确认',
      { confirmButtonText: '确定移除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    const res = await api.delete(`/watchlist/${row.code}`)
    if (res.code === 0) {
      ElMessage.success(`已移除 ${row.name}`)
      clearDashboardSnapshot()
      await loadDashboardParallel()
      writeDashboardSnapshot()
    } else {
      ElMessage.error(res.message || '移除失败')
    }
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

// =========================================================================
// 生命周期
// =========================================================================

/**
 * 仪表盘三大板块并行请求：
 * - 指数卡片：内部已对 4 个指数并发 GET（Promise.all）
 * - 自选股：先拉列表再对多只股票并发询价（Promise.all）
 * - 热点快讯：单次 GET
 * 三者之间用 Promise.allSettled 同时发起，互不阻塞；任一失败不影响其它板块展示。
 */
async function loadDashboardParallel() {
  await Promise.allSettled([
    loadIndices(),
    loadWatchlist(),
    loadHotNews(),
  ])
}

/**
 * 10 分钟内复用本地快照，不再请求后端（后端妙想链路亦有 TTL 缓存）。
 * KeepAlive 返回本页时通过 onActivated 再次命中快照。
 */
async function loadDashboardWithClientCache() {
  const snap = readDashboardSnapshot()
  if (snap && Date.now() - snap.ts < DASHBOARD_CACHE_TTL_MS) {
    applyDashboardSnapshot(snap)
    return
  }
  await loadDashboardParallel()
  writeDashboardSnapshot()
}

/**
 * 进入仪表盘时：
 * - 若其它页曾变更自选（localStorage 待刷新标记），跳过快照强制全量拉取，自选必为新；
 * - 否则沿用 TTL 内快照，减轻请求。
 */
async function hydrateDashboard() {
  const pendingWl = consumeWatchlistRefreshPending()
  if (pendingWl) {
    clearDashboardSnapshot()
    await loadDashboardParallel()
    writeDashboardSnapshot()
    return
  }
  await loadDashboardWithClientCache()
}

/** 其他页加入自选后：立即刷新（当前若在仪表盘且组件已挂载会收到事件） */
function onWatchlistChangedExternally() {
  clearDashboardSnapshot()
  consumeWatchlistRefreshPending()
  loadDashboardParallel().then(() => writeDashboardSnapshot())
}

onMounted(() => {
  window.addEventListener(WATCHLIST_CHANGED_EVENT, onWatchlistChangedExternally)
  hydrateDashboard()
})

onActivated(() => {
  hydrateDashboard()
})

onUnmounted(() => {
  window.removeEventListener(WATCHLIST_CHANGED_EVENT, onWatchlistChangedExternally)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  color: #303133;
}

/* 指数卡片行 */
.index-row {
  margin-bottom: 16px;
}

.index-card {
  text-align: center;
  cursor: default;
}
.index-card :deep(.el-card__body) {
  padding: 20px 12px;
}
.index-name {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.index-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 6px;
  font-family: 'DIN', 'Helvetica Neue', monospace;
}
.index-change {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.index-change.up {
  color: #f56c6c;
}
.index-change.down {
  color: #1ecd94;
}
.change-icon {
  font-size: 12px;
}
.change-unit {
  font-size: 12px;
  font-weight: 400;
}

/* 内容双栏 */
.content-row {
  align-items: flex-start;
}

/* 卡片通用 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.card-title-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
@media (min-width: 900px) {
  .card-title-row {
    flex-direction: row;
    align-items: baseline;
    gap: 10px;
  }
}

.watchlist-card,
.news-card {
  height: 100%;
}

/* 行情颜色 */
.text-up {
  color: #f56c6c;
}
.text-down {
  color: #1ecd94;
}

/* 热点快讯列表 */
.news-list {
  max-height: 480px;
  overflow-y: auto;
}
.news-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}
.news-item:last-child {
  border-bottom: none;
}
.news-item:hover {
  background: #f5f7fa;
}
.news-title {
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.news-date {
  font-size: 11px;
  color: #c0c4cc;
}

/* 表格点击样式 */
.el-table tbody tr {
  cursor: pointer;
}
</style>
