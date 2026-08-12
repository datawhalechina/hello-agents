<template>
  <div class="analysis-page">
    <!-- 搜索栏（无股票代码时显示） -->
    <div v-if="!stockCode" class="search-section">
      <h2>股票分析</h2>
      <el-text type="info" style="display:block; margin-bottom:20px;">
        输入股票代码，获取深度分析报告
      </el-text>
      <el-input
        v-model="searchInput"
        placeholder="输入6位股票代码，如 600519（贵州茅台）"
        class="search-input"
        size="large"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            开始分析
          </el-button>
        </template>
      </el-input>
      <div class="stock-examples">
        <span class="example-label">热门股票：</span>
        <span v-for="s in hotStocks" :key="s.code" class="hot-stock-wrap">
          <el-tag
            class="example-tag"
            type="info"
            @click="selectStock(s.code)"
          >
            {{ s.name }}（{{ s.code }}）
          </el-tag>
          <el-button
            type="warning"
            link
            size="small"
            class="hot-add-wl"
            :loading="quickWlLoading === s.code"
            @click.stop="handleQuickAddWatchlist(s.code)"
          >
            <el-icon><Star /></el-icon>
          </el-button>
        </span>
      </div>
    </div>

    <!-- 分析内容（有股票代码时显示） -->
    <template v-if="stockCode">
      <!-- 股票头部信息 -->
      <div class="stock-header">
        <div class="header-info">
          <h2>{{ stockName }} <span class="stock-code">{{ stockCode }}</span></h2>
          <el-text type="info" v-if="profileData.company_name">
            {{ profileData.company_name }}
          </el-text>
        </div>
        <!-- `--` 等为「暂无数据」占位，不是股票名称；名称在左侧标题 -->
        <div class="header-quote" v-if="showHeaderQuote">
          <div class="quote-price">{{ quoteData.price }}</div>
          <div
            v-if="quoteChangeDisplay.text"
            :class="['quote-change', quoteChangeDisplay.cls]"
          >
            {{ quoteChangeDisplay.text }}
          </div>
        </div>
        <el-text v-else-if="stockCode && !quoteLoading" type="info" size="small">
          暂无实时行情
        </el-text>
        <div class="header-actions">
          <el-button
            type="warning"
            plain
            :loading="watchlistBtnLoading"
            @click="handleAddCurrentToWatchlist"
          >
            <el-icon><Star /></el-icon>
            加自选
          </el-button>
          <el-button @click="stockCode = ''; searchInput = ''">更换股票</el-button>
        </div>
      </div>

      <!-- 分析标签页 -->
      <el-tabs v-model="activeTab" type="border-card" class="analysis-tabs">
        <!-- lazy：仅首次进入该标签时才挂载内容，避免未选中的标签（如巴菲特）里的大按钮出现在布局最上方 -->
        <!-- Tab 1: 行情图表（优先加载，与头部报价同源） -->
        <el-tab-pane label="行情图表" name="chart" lazy>
          <div v-loading="quoteLoading" class="chart-tab-body">
            <div class="chart-container">
              <v-chart :option="chartOption" autoresize style="height: 400px;" />
            </div>
            <!-- 行情数据明细 -->
            <el-descriptions :column="4" border class="quote-detail" v-if="quoteData.raw">
              <el-descriptions-item
                v-for="(val, key) in quoteExtracted"
                :key="key"
                :label="key"
              >
                {{ val }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 财务数据 -->
        <el-tab-pane label="财务数据" name="financial" lazy>
          <div v-loading="finLoading">
            <!-- 财务指标卡片 -->
            <el-row :gutter="16" v-if="finData.length > 0">
              <el-col :span="6" v-for="item in finData" :key="item.label">
                <el-card shadow="hover" class="fin-card">
                  <div class="fin-label">{{ item.label }}</div>
                  <div class="fin-value">{{ item.value }}</div>
                </el-card>
              </el-col>
            </el-row>
            <el-empty v-else-if="!finLoading" description="暂无财务数据" :image-size="60" />

            <!-- 公司概况：宽表字段用描述列表网格展示，长文案占满一行 -->
            <el-card shadow="hover" class="profile-card" v-if="profileData.entries?.length">
              <template #header><span class="card-title">公司概况</span></template>
              <el-descriptions
                :column="2"
                border
                size="small"
                class="profile-desc"
              >
                <el-descriptions-item
                  v-for="(row, idx) in profileData.entries"
                  :key="idx"
                  :label="row.label"
                  :span="row.span"
                >
                  <span class="profile-value">{{ row.value }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 十大股东 -->
            <el-card shadow="hover" class="holders-card" v-if="holdersData.length > 0">
              <template #header><span class="card-title">十大股东</span></template>
              <el-table
                :data="holdersData"
                stripe
                border
                size="small"
                class="holders-table"
                style="width: 100%"
              >
                <el-table-column
                  prop="name"
                  label="股东名称"
                  min-width="200"
                  show-overflow-tooltip
                />
                <el-table-column
                  v-if="holdersShowRatioColumn"
                  prop="ratio"
                  label="持股比例"
                  width="120"
                  align="right"
                />
                <el-table-column
                  v-if="holdersShowSharesColumn"
                  prop="shares"
                  label="持股数量"
                  min-width="140"
                  align="right"
                />
              </el-table>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- Tab 3: AI舆情分析 -->
        <el-tab-pane label="AI舆情分析" name="sentiment" lazy>
          <AIAnalysisPanel
            :stockCode="stockCode"
            :stockName="stockName"
            apiEndpoint="/agent/sentiment/stream"
            historyType="sentiment"
            buttonLabel="AI舆情分析"
            buttonType="warning"
            buttonIcon="ChatLineSquare"
            description="点击按钮，AI将自动搜索最新资讯并分析市场舆情，结果以流式输出"
          />
        </el-tab-pane>

        <!-- Tab 4: AI数据分析 -->
        <el-tab-pane label="AI数据分析" name="data_analysis" lazy>
          <AIAnalysisPanel
            :stockCode="stockCode"
            :stockName="stockName"
            apiEndpoint="/agent/data-analysis/stream"
            historyType="data_analysis"
            buttonLabel="AI数据分析"
            buttonType="primary"
            buttonIcon="TrendCharts"
            description="点击按钮，AI将自动查询行情、财务数据并进行分析，结果以流式输出"
          />
        </el-tab-pane>

        <!-- Tab 5: 巴菲特评估 -->
        <el-tab-pane label="巴菲特评估" name="buffett" lazy>
          <div class="buffett-section">
            <div class="buffett-generate" v-if="!buffettStreaming && !buffettAiMarkdown.trim()">
              <el-empty description="点击下方按钮开始巴菲特式价值投资评估" :image-size="72">
                <el-button
                  type="danger"
                  size="large"
                  :loading="buffettStreaming"
                  @click="runBuffettAiReportStream"
                >
                  <el-icon><MagicStick /></el-icon> 生成巴菲特评估报告
                </el-button>
              </el-empty>
            </div>

            <div v-if="buffettStreaming && buffettStreamRaw" class="buffett-stream-wrap">
              <div class="buffett-stream-label">正在生成（实时预览）</div>
              <pre class="buffett-stream-pre">{{ buffettStreamRaw }}<span class="buffett-stream-caret">&#x258D;</span></pre>
            </div>

            <div v-if="buffettStreaming && !buffettStreamRaw" class="buffett-stream-wait">
              <el-icon class="is-loading" :size="28"><Loading /></el-icon>
              <span>正在准备数据并连接模型...</span>
            </div>

            <div v-if="buffettAiMarkdown.trim() && !buffettStreaming" class="buffett-ai-wrap">
              <div class="buffett-ai-header">
                <h3 class="buffett-title">巴菲特价值投资评估报告</h3>
                <div class="buffett-ai-header-actions">
                  <el-button size="small" @click="runBuffettAiReportStream" :loading="buffettStreaming">重新生成</el-button>
                  <el-button size="small" type="primary" plain @click="downloadBuffettReport"><el-icon><Download /></el-icon>下载报告</el-button>
                  <el-button text type="danger" @click="clearBuffettAiReport">清除</el-button>
                </div>
              </div>
              <div class="buffett-template-body buffett-ai-body" v-html="buffettAiReportHtml" />
            </div>

            <el-alert v-if="buffettAiError && !buffettStreaming" type="warning" :closable="false" show-icon :title="buffettAiError" class="buffett-error-alert" />

            <div style="margin-top: 12px; text-align: right;">
              <el-button size="small" @click="historyVisibleBuffett = true"><el-icon><Clock /></el-icon>历史记录</el-button>
            </div>
            <HistoryDrawer v-model:visible="historyVisibleBuffett" type="buffett" />
          </div>
        </el-tab-pane>

        <!-- Tab 6: AI对话助手 -->
        <el-tab-pane label="AI对话助手" name="chat" lazy>
          <ChatAssistant
            :stockCode="stockCode"
            :stockName="stockName"
            :chat-visible="activeTab === 'chat'"
          />
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script>
export default { name: 'StockAnalysis' }
</script>

<script setup>
/**
 * 股票分析页面
 *
 * 提供个股深度分析功能：行情图表、财务数据、舆情分析、AI分析报告。
 * 路由参数 :code 可选，未指定时显示搜索框。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Star, MagicStick, Download } from '@element-plus/icons-vue'
import api, { fetchWithRetry } from '@/api'
import AIAnalysisPanel from '@/components/AIAnalysisPanel.vue'
import ChatAssistant from '@/components/ChatAssistant.vue'
import HistoryDrawer from '@/components/HistoryDrawer.vue'
import { addStockToWatchlist } from '@/utils/watchlist'

// =========================================================================
// ECharts 注册（K线图所需组件）
// =========================================================================
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  ToolboxComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  ToolboxComponent,
  MarkLineComponent,
])

// =========================================================================
// 路由
// =========================================================================
const route = useRoute()
const router = useRouter()

// 热门股票快捷入口
const hotStocks = [
  { name: '贵州茅台', code: '600519' },
  { name: '比亚迪', code: '002594' },
  { name: '宁德时代', code: '300750' },
  { name: '招商银行', code: '600036' },
  { name: '中国平安', code: '601318' },
]

// =========================================================================
// 响应式状态
// =========================================================================
const searchInput = ref('')
const stockCode = ref('')
const stockName = ref('')
const loading = ref(false)
/** 仅行情与图表区域 loading（与财务/舆情异步） */
const quoteLoading = ref(false)
const activeTab = ref('chart')

// 行情数据
const quoteData = ref({ price: null, change: null, raw: null })
const quoteExtracted = ref({})

// 财务数据
const finData = ref([])
const finLoading = ref(false)
const profileData = ref({})
const holdersData = ref([])

/** 十大股东单元格是否为有效数据（无数据则不展示整列，避免出现满屏「--」） */
function holderMetricCellHasData(val) {
  if (val == null) return false
  const s = String(val).trim()
  if (!s || s === '--' || s === '—' || s === '-' || s === '暂无') return false
  return true
}

const holdersShowRatioColumn = computed(() =>
  holdersData.value.some((r) => holderMetricCellHasData(r.ratio)),
)
const holdersShowSharesColumn = computed(() =>
  holdersData.value.some((r) => holderMetricCellHasData(r.shares)),
)

// 巴菲特评估：NDJSON 流式 POST /buffett/report/generate-ai/stream
const buffettStreaming = ref(false)
const buffettStreamRaw = ref('')
const buffettAiMarkdown = ref('')
const buffettAiError = ref('')
const historyVisibleBuffett = ref(false)

function escapeHtmlText(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** 巴菲特模板：先转义防 v-html 截断，再渲染标题/加粗/换行 */
function formatBuffettReportHtml(md) {
  let t = escapeHtmlText(md || '')
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  t = t.replace(/^#### (.+)$/gm, '<h5>$1</h5>')
  t = t.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  t = t.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  t = t.replace(/^# (.+)$/gm, '<h2>$1</h2>')
  t = t.replace(/\n/g, '<br>')
  return t
}

const buffettAiReportHtml = computed(() =>
  formatBuffettReportHtml(buffettAiMarkdown.value || ''),
)

const watchlistBtnLoading = ref(false)
/** 搜索页热门股旁「加自选」按钮 loading */
const quickWlLoading = ref('')

/** 名称列：行情表里常见「证券简称」等；若无则用热门股列表兜底（避免标题只剩代码） */
function pickStockNameFromDict(dict, code) {
  const skipKey = /代码|编号|类别|交易所|^市场|类型/
  for (const [k, v] of Object.entries(dict)) {
    if (skipKey.test(k)) continue
    if (!/名称|简称/.test(k)) continue
    const s = String(v ?? '').trim()
    if (s && s !== '--' && s !== '—') return s
  }
  const hit = hotStocks.find((s) => s.code === code)
  return hit?.name ?? ''
}

function isPlaceholderQuote(val) {
  if (val == null || val === '') return true
  const s = String(val).trim()
  return s === '--' || s === '—' || s === '-' || s === '暂无'
}

/** 头部报价区：有真实价格时才展示，避免大号 `--` 被误认为名称 */
const showHeaderQuote = computed(() => !isPlaceholderQuote(quoteData.value.price))

function parseChangeForDisplay(val) {
  if (isPlaceholderQuote(val)) return { text: '', cls: '', num: null }
  const raw = String(val).trim()
  const n = parseFloat(raw.replace(/[%％]/g, ''))
  if (!Number.isFinite(n)) return { text: '', cls: '', num: null }
  const hasPct = /%|％/.test(raw)
  const text = hasPct
    ? `${n >= 0 ? '+' : ''}${raw.replace(/^\+/, '')}`
    : `${n >= 0 ? '+' : ''}${n}%`
  return { text, cls: n >= 0 ? 'up' : 'down', num: n }
}

const quoteChangeDisplay = computed(() => {
  const { text, cls } = parseChangeForDisplay(quoteData.value.change)
  return { text, cls }
})

// =========================================================================
// ECharts 图表配置（当日五价快照连线，不是历史 K 线）
// =========================================================================
/** 从行情宽表按候选列名取第一个可解析数值（兼容千分位） */
function pickQuoteNumber(extracted, keys) {
  for (const k of keys) {
    const raw = extracted[k]
    if (raw == null || raw === '') continue
    const n = parseFloat(String(raw).replace(/,/g, ''))
    if (Number.isFinite(n) && n > 0) return n
  }
  return null
}

/** 五价完全相同时拉开 Y 轴，避免 ECharts 画成「一条看不见的线」 */
function chartYAxisBoundsFromSeries(data) {
  const nums = data.map(Number).filter((n) => Number.isFinite(n) && n > 0)
  if (nums.length === 0) return {}
  const minV = Math.min(...nums)
  const maxV = Math.max(...nums)
  if (minV === maxV) {
    const pad = Math.max(minV * 0.0015, 0.01)
    return { min: minV - pad, max: maxV + pad }
  }
  const span = maxV - minV
  const margin = Math.max(span * 0.12, 0.01)
  return { min: minV - margin, max: maxV + margin }
}

const chartOption = computed(() => {
  const seriesData = quotePriceArray.value
  const yBounds = chartYAxisBoundsFromSeries(seriesData)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 16, top: 56, bottom: 40, containLabel: true },
    title: {
      text: stockCode.value ? `${stockName.value || stockCode.value} 当日价位快照` : '',
      subtext: '由开盘/高/低/收/昨收组成的截面数据，非历史走势；缺字段时可能接近平线',
      left: 'center',
      subtextStyle: { fontSize: 11, color: '#909399' },
    },
    toolbox: {
      feature: {
        dataZoom: { yAxisIndex: 'none' },
        restore: {},
        saveAsImage: {},
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['开盘', '最高', '最低', '收盘', '昨收'],
    },
    yAxis: {
      type: 'value',
      scale: true,
      ...yBounds,
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: '价格',
        type: 'line',
        data: seriesData,
        markLine: {
          silent: true,
          data: [{ type: 'average', name: '五价均值' }],
        },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64,158,255,0.3)' },
              { offset: 1, color: 'rgba(64,158,255,0.02)' },
            ],
          },
        },
      },
    ],
  }
})

const quotePriceArray = computed(() => {
  const q = quoteData.value
  if (!q.raw) return [0, 0, 0, 0, 0]
  const extracted = {}
  if (q.raw?.tables && q.raw.tables[0]) {
    const t = q.raw.tables[0]
    const names = t.fieldnames || t.fieldNames || []
    const row0 = t.rows?.[0]
    if (row0) {
      names.forEach((name, i) => {
        extracted[name] = cellAt(names, row0, i)
      })
    }
  }

  const price =
    pickQuoteNumber(extracted, ['最新价', '现价', '收盘价', '最新']) ??
    (() => {
      const n = parseFloat(String(q.price ?? '').replace(/,/g, ''))
      return Number.isFinite(n) && n > 0 ? n : null
    })()

  if (price == null) return [0, 0, 0, 0, 0]

  const chgAmt = pickQuoteNumber(extracted, ['涨跌额'])
  let prevClose = pickQuoteNumber(extracted, [
    '昨收',
    '昨收盘价',
    '前收盘',
    '前收盘价',
    '昨日收盘',
    '昨收价',
  ])
  if (prevClose == null && chgAmt != null) prevClose = price - chgAmt
  if (prevClose == null) prevClose = price

  let open = pickQuoteNumber(extracted, ['今开', '开盘', '开盘价', '今日开盘价'])
  if (open == null) open = prevClose

  let high = pickQuoteNumber(extracted, ['最高', '最高价', '今日最高'])
  if (high == null) high = Math.max(price, open)

  let low = pickQuoteNumber(extracted, ['最低', '最低价', '今日最低'])
  if (low == null) low = Math.min(price, open)

  return [open, high, low, price, prevClose]
})

// =========================================================================
// 数据解析工具（mx_data 的 rows 为对象数组，列名为 key，不能用 rows[0][i]）
// =========================================================================
function cellAt(names, row, colIdx) {
  if (colIdx < 0 || row == null) return undefined
  if (Array.isArray(row)) return row[colIdx]
  const key = names[colIdx]
  return key != null ? row[key] : undefined
}

function parseTableToDict(data) {
  /** 将 mx-data 表格第一行转为键值对（宽表） */
  const result = {}
  if (!data?.tables) return result
  for (const table of data.tables) {
    const names = table.fieldnames || table.fieldNames || []
    const rows = table.rows || []
    if (rows.length > 0) {
      const row = rows[0]
      for (let i = 0; i < names.length; i++) {
        const k = names[i]
        if (k != null) result[k] = cellAt(names, row, i)
      }
    }
  }
  return result
}

function parseTableToCards(data) {
  /** 将 mx-data 表格数据转为卡片数据 */
  const dict = parseTableToDict(data)
  return Object.entries(dict).map(([label, value]) => ({ label, value }))
}

/**
 * 妙想 mx_data 对带 headName 维度的宽表将第一列固定命名为 date（见 skills/金融数据/mx-data），
 * 在公司概况/主营构成等场景下该列实为报告期或业务分项，不应展示为英文 date。
 */
function normalizeProfileFieldLabel(label, raw) {
  const k = String(label ?? '').trim()
  if (!/^date$/i.test(k)) return k
  const v = String(raw ?? '').trim()
  if (!v || v === '--') return '维度'
  if (
    /^\d{4}([-/.年]\d{1,2})?([-/.月]\d{1,2})?(日)?$/.test(v) ||
    /^\d{8}$/.test(v) ||
    /年报|中报|季报|半年报|第一季|第二季|第三季|第四季|报告期|截至|截止|期末/.test(v)
  ) {
    return '报告期'
  }
  return '项目'
}

function parseProfileData(data) {
  /** 解析公司概况：生成描述列表行；长字段跨两列便于阅读 */
  if (!data?.tables) return { company_name: '', entries: [] }
  const dict = parseTableToDict(data)
  const company_name =
    dict['证券简称'] ??
    dict['股票简称'] ??
    dict['A股简称'] ??
    dict['公司名称'] ??
    ''
  // 排除与页头重复的股票代码类字段（勿用 /[代码|编号]/：字符类里 | 只是普通字符）
  const skipKey = (k) => {
    const s = String(k).trim()
    return s === '证券代码' || s === '股票代码' || s === '代码'
  }

  const longLabel = (label, value) =>
    /简介|范围|业务|介绍|概况|描述|主营|项目/.test(String(label)) ||
    String(value || '').length > 100

  const entries = Object.entries(dict)
    .filter(([k]) => k != null && String(k).trim() !== '')
    .filter(([k]) => !skipKey(k))
    .map(([label, raw]) => {
      const value =
        raw == null || raw === '' ? '--' : String(raw).trim() === '' ? '--' : String(raw)
      const displayLabel = normalizeProfileFieldLabel(label, raw)
      return {
        label: displayLabel,
        value,
        span: longLabel(displayLabel, value) ? 2 : 1,
      }
    })

  return { company_name, entries }
}

/** 根据表头挑选十大股东各列（避免「持股变动」等命中错误的「持股」列） */
function pickHolderColumnIndices(names) {
  const list = (names || []).map((s) => String(s))
  const idx = (pred) => list.findIndex(pred)

  const namePrefer = ['股东名称', '持有人名称', '十大股东名称', '流通股东名称']
  let nameIdx = -1
  for (const p of namePrefer) {
    nameIdx = idx((h) => h.includes(p))
    if (nameIdx >= 0) break
  }
  if (nameIdx < 0) {
    // 妙想 mx_data 解析把维度列统一命名为 date，十大股东场景下常为股东名或报告期
    nameIdx = idx((h) => /^(date|Date)$/.test(h))
  }
  if (nameIdx < 0) {
    nameIdx = idx((h) => /名称/.test(h) && !/(代码|简称|证券)/.test(h))
  }
  if (nameIdx < 0) {
    nameIdx = idx((h) => /股东/.test(h) && !/(性质|类别|类型|变动|比例|数量)/.test(h))
  }

  const ratioPrefer = ['持股比例', '占总股本比例', '持股占总股本比例', '持股比例(%)', '持股占比']
  let ratioIdx = -1
  for (const p of ratioPrefer) {
    ratioIdx = idx((h) => h.includes(p))
    if (ratioIdx >= 0) break
  }
  if (ratioIdx < 0) {
    ratioIdx = idx(
      (h) =>
        /比例|占比/.test(h) &&
        !/(变动|市值|性质|类别|类型|增减|人数)/.test(h),
    )
  }

  const sharesPrefer = ['持股数量', '持有数量', '期末持股数量', '期末持股数', '持股股数', '持股(股)']
  let sharesIdx = -1
  for (const p of sharesPrefer) {
    sharesIdx = idx((h) => h.includes(p))
    if (sharesIdx >= 0) break
  }
  if (sharesIdx < 0) {
    sharesIdx = idx(
      (h) =>
        (/数量|股数/.test(h) || /^持股$/.test(h)) &&
        !/比例|占比|变动|市值/.test(h),
    )
  }

  return { nameIdx, ratioIdx, sharesIdx }
}

/** 首行即有非空单元格的对象行（避免标题空行误导 fieldnames 对齐） */
function firstDictRowWithValues(rows) {
  for (const row of rows || []) {
    if (row != null && typeof row === 'object' && !Array.isArray(row)) {
      const vals = Object.values(row).filter((v) => v != null && String(v).trim() !== '')
      if (vals.length) return row
    }
  }
  return null
}

/** fieldnames 与 row 的 key 不一致时用首行实际 key 列表 */
function resolveHolderFieldnames(table) {
  let names = table.fieldnames || table.fieldNames || []
  const rows = table.rows || []
  const r0 = firstDictRowWithValues(rows)
  if (!r0) return names

  const keys = Object.keys(r0)
  const nonempty = (ns, colIdx) => {
    if (colIdx < 0 || !ns.length) return false
    const v = cellAt(ns, r0, colIdx)
    return v != null && String(v).trim() !== ''
  }

  const picked = pickHolderColumnIndices(names)
  const ok =
    nonempty(names, picked.nameIdx) ||
    nonempty(names, picked.ratioIdx) ||
    nonempty(names, picked.sharesIdx)

  if (!ok && keys.length) return keys
  return names
}

/** 妙想常见「两列长表」：列名为证券名+报告期，首列为指标名、次列为数值 */
function shouldTryVerticalHolders(table) {
  const fn = table.fieldnames || []
  const rows = table.rows || []
  if (fn.length !== 2 || rows.length < 2) return false
  const k = fn[0]
  const hits = rows.slice(0, 50).filter((row) => {
    const label = String(row[k] ?? '').trim()
    return (
      /^(股东名称|持有人名称|持股比例|持股数量|占总股本比例|持股数量\(股\)|期末持股数量)/.test(label) ||
      label === '名称'
    )
  }).length
  return hits >= 2
}

function parseHoldersVerticalTwoCol(table, { force = false } = {}) {
  const fn = table.fieldnames || []
  const rows = table.rows || []
  if (fn.length !== 2 || !rows.length) return []
  if (!force && !shouldTryVerticalHolders(table)) return []

  const kLabel = fn[0]
  const kVal = fn[1]
  const holders = []
  let cur = null

  const flush = () => {
    if (!cur) return
    if (cur.name || cur.ratio || cur.shares) {
      holders.push({
        name: cur.name != null && String(cur.name).trim() !== '' ? cur.name : '--',
        ratio: cur.ratio != null && String(cur.ratio).trim() !== '' ? cur.ratio : '--',
        shares: cur.shares != null && String(cur.shares).trim() !== '' ? cur.shares : '--',
      })
    }
    cur = null
  }

  for (const row of rows) {
    const label = String(row[kLabel] ?? '').trim()
    const val = row[kVal]
    const valStr = val == null ? '' : String(val).trim()
    if (!label) continue

    if (/股东\s*名称|持有人\s*名称/.test(label) || label === '名称') {
      flush()
      cur = { name: valStr, ratio: undefined, shares: undefined }
      continue
    }
    if (/第\s*\d+\s*(名|大)?\s*股东/.test(label)) {
      flush()
      cur = { name: valStr, ratio: undefined, shares: undefined }
      continue
    }

    if (!cur) cur = { name: undefined, ratio: undefined, shares: undefined }

    if (/比例|占比/.test(label) && !/数量/.test(label)) cur.ratio = valStr
    else if (/数量|股数/.test(label)) cur.shares = valStr
  }
  flush()
  return holders
}

function holderRowHasValue(h) {
  return (
    (h.name && h.name !== '--') ||
    (h.ratio && h.ratio !== '--') ||
    (h.shares && h.shares !== '--')
  )
}

function parseHoldersData(data) {
  /** 解析股东数据（宽表 / 两列长表 / fieldnames 与 key 不一致） */
  if (!data?.tables) return []
  const holders = []
  for (const table of data.tables) {
    let vertical = parseHoldersVerticalTwoCol(table)
    if (vertical.length && vertical.some(holderRowHasValue)) {
      holders.push(...vertical)
      continue
    }

    let names = resolveHolderFieldnames(table)
    let { nameIdx, ratioIdx, sharesIdx } = pickHolderColumnIndices(names)
    const batch = []

    for (const row of table.rows || []) {
      let name = nameIdx >= 0 ? cellAt(names, row, nameIdx) : undefined
      let ratio = ratioIdx >= 0 ? cellAt(names, row, ratioIdx) : undefined
      let shares = sharesIdx >= 0 ? cellAt(names, row, sharesIdx) : undefined
      if (row != null && typeof row === 'object' && !Array.isArray(row)) {
        const o = row
        const pick = (patterns) => {
          for (const k of Object.keys(o)) {
            if (patterns.some((re) => re.test(k))) return o[k]
          }
          return undefined
        }
        if (name == null || String(name).trim() === '') {
          name =
            pick([/股东名称|持有人/, /^(date|Date)$/]) ??
            pick([/名称/, /股东[^类]*$/])
        }
        if (ratio == null || String(ratio).trim() === '') {
          ratio = pick([/持股比例|占总股本比例|持股占比|持有比例/, /^比例$/])
        }
        if (shares == null || String(shares).trim() === '') {
          shares = pick([/持股数量|持有数量|期末持股|股数/, /^持股$/])
        }
      }

      batch.push({
        name: name != null && String(name).trim() !== '' ? name : '--',
        ratio: ratio != null && String(ratio).trim() !== '' ? ratio : '--',
        shares: shares != null && String(shares).trim() !== '' ? shares : '--',
      })
    }

    if (batch.length && !batch.some(holderRowHasValue) && (table.fieldnames || []).length === 2) {
      vertical = parseHoldersVerticalTwoCol(table, { force: true })
      if (vertical.some(holderRowHasValue)) {
        holders.push(...vertical)
        continue
      }
    }

    holders.push(...batch)
  }
  return holders
}

// =========================================================================
// 数据加载
// =========================================================================

/** 统一解包：拦截器已返回 { code, message, data, meta } */
function unwrapData(res) {
  if (!res || res.code !== 0 || res.data == null) return null
  return res.data
}

/** 切换股票时递增，防止异步请求乱序覆盖 */
let analysisLoadSeq = 0

/** 将行情接口结果写入头部与图表依赖的状态 */
function applyQuotePayload(quoteRes) {
  if (quoteRes?.success) {
    const dict = parseTableToDict(quoteRes)
    const priceRaw =
      dict['最新价'] ?? dict['现价'] ?? dict['收盘价'] ?? dict['最新'] ?? null
    const changeRaw = dict['涨跌幅'] ?? dict['当日涨跌幅'] ?? dict['涨跌幅度'] ?? null
    quoteData.value = {
      price: isPlaceholderQuote(priceRaw) ? null : priceRaw,
      change: isPlaceholderQuote(changeRaw) ? null : changeRaw,
      raw: quoteRes,
    }
    quoteExtracted.value = dict
    const nm = pickStockNameFromDict(dict, stockCode.value)
    if (nm) stockName.value = nm
  } else {
    quoteData.value = { price: null, change: null, raw: null }
    quoteExtracted.value = {}
  }
}

/** 第二阶段：财务 / 概况 / 股东（与行情并行解耦，_tab 内单独 loading） */
async function loadSecondaryAnalysis(seq) {
  if (!stockCode.value || seq !== analysisLoadSeq) return

  finLoading.value = true

  try {
    const [finRes, profileRes, holdersRes] = await Promise.all([
      api.get(`/financial/indicators/${stockCode.value}`).then(unwrapData).catch(() => null),
      api.get(`/financial/profile/${stockCode.value}`).then(unwrapData).catch(() => null),
      api.get(`/financial/holders/${stockCode.value}`).then(unwrapData).catch(() => null),
    ])

    if (seq !== analysisLoadSeq) return

    if (finRes?.success) {
      finData.value = parseTableToCards(finRes)
    } else {
      finData.value = []
    }

    if (profileRes?.success) {
      profileData.value = parseProfileData(profileRes)
    } else {
      profileData.value = { company_name: '', entries: [] }
    }

    if (holdersRes?.success) {
      holdersData.value = parseHoldersData(holdersRes)
    } else {
      holdersData.value = []
    }
  } finally {
    if (seq === analysisLoadSeq) {
      finLoading.value = false
    }
  }
}

/**
 * 加载分析数据：先行情（头部 + 图表 Tab），再后台拉财务/概况/股东/舆情。
 */
async function loadAllData() {
  if (!stockCode.value) return
  const seq = ++analysisLoadSeq

  // 切换代码时清空展示数据，避免图表/报价短暂停留在上一只股票
  quoteData.value = { price: null, change: null, raw: null }
  quoteExtracted.value = {}
  profileData.value = { company_name: '', entries: [] }
  holdersData.value = []
  finData.value = []
  buffettAiMarkdown.value = ''
  buffettStreamRaw.value = ''
  buffettAiError.value = ''

  loading.value = true
  quoteLoading.value = true
  stockName.value = pickStockNameFromDict({}, stockCode.value)

  try {
    const quoteRes = await api
      .get(`/market/quote/${stockCode.value}`)
      .then(unwrapData)
      .catch(() => null)

    if (seq !== analysisLoadSeq) return

    applyQuotePayload(quoteRes)
  } finally {
    if (seq === analysisLoadSeq) {
      quoteLoading.value = false
      loading.value = false
    }
  }

  loadSecondaryAnalysis(seq)
}

/** 下载当前巴菲特报告为 Markdown 文件 */
function downloadBuffettReport() {
  const md = (buffettAiMarkdown.value || '').trim()
  if (!md) {
    ElMessage.warning('暂无报告可下载')
    return
  }
  const rawCode = (stockCode.value || 'stock').trim() || 'stock'
  const safeCode = rawCode.replace(/[\\/:*?"<>|]/g, '_')
  const d = new Date()
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
  const filename = `巴菲特评估_${safeCode}_${stamp}.md`
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('报告已开始下载')
}

/** 流式生成巴菲特 AI 评估报告（fetch + NDJSON，无 axios 全局超时限制） */
async function runBuffettAiReportStream() {
  if (!stockCode.value) return
  buffettStreaming.value = true
  buffettStreamRaw.value = ''
  buffettAiMarkdown.value = ''
  buffettAiError.value = ''
  try {
    const res = await fetchWithRetry('/api/v1/buffett/report/generate-ai/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/x-ndjson',
      },
      body: JSON.stringify({
        stock_code: stockCode.value.trim(),
        stock_name: (stockName.value || '').trim(),
      }),
    })
    if (!res.ok) {
      const t = await res.text()
      let msg = t || res.statusText
      try {
        const j = JSON.parse(t)
        if (j.message) msg = j.message
      } catch {
        /* ignore */
      }
      throw new Error(msg)
    }
    const reader = res.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')

    const dec = new TextDecoder()
    let buf = ''
    let streamError = null
    let streamFinished = false

    while (true) {
      const { done: readerDone, value } = await reader.read()
      if (value) buf += dec.decode(value, { stream: true })

      let nl
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl).trim()
        buf = buf.slice(nl + 1)
        if (!line) continue
        let obj
        try {
          obj = JSON.parse(line)
        } catch {
          continue
        }
        const deltaPiece = obj.text ?? obj.content
        if (obj.type === 'delta' && deltaPiece) {
          buffettStreamRaw.value += deltaPiece
        } else if (obj.type === 'error') {
          streamError = obj.message || obj.content || '生成失败'
        } else if (obj.type === 'done') {
          streamFinished = true
        }
      }

      if (streamError) throw new Error(streamError)
      if (streamFinished || readerDone) break
    }

    const tail = buf.trim()
    if (tail) {
      try {
        const obj = JSON.parse(tail)
        if (obj.type === 'error') throw new Error(obj.message || obj.content || '生成失败')
        const tailDelta = obj.text ?? obj.content
        if (obj.type === 'delta' && tailDelta) buffettStreamRaw.value += tailDelta
      } catch (e) {
        if (!(e instanceof SyntaxError)) throw e
      }
    }

    const md = buffettStreamRaw.value.trim()
    buffettAiMarkdown.value = md
    buffettStreamRaw.value = ''
    if (!md) {
      buffettAiError.value = '模型未返回有效内容'
      ElMessage.warning(buffettAiError.value)
    } else {
      ElMessage.success('巴菲特评估报告已生成')
    }
  } catch (e) {
    const msg = e?.message || '请求失败'
    const isAbort = /aborted|timeout|AbortError/i.test(msg)
    buffettAiError.value = isAbort
      ? '连接超时或中断。可在 .env 增大 LLM_TIMEOUT 后重启后端，或检查网络后重试。'
      : msg
    ElMessage.error(buffettAiError.value)
    buffettAiMarkdown.value = ''
    buffettStreamRaw.value = ''
  } finally {
    buffettStreaming.value = false
  }
}

function clearBuffettAiReport() {
  buffettAiMarkdown.value = ''
  buffettStreamRaw.value = ''
  buffettAiError.value = ''
}

// =========================================================================
// 交互
// =========================================================================

async function handleAddCurrentToWatchlist() {
  if (!stockCode.value) return
  watchlistBtnLoading.value = true
  try {
    await addStockToWatchlist(stockCode.value)
  } finally {
    watchlistBtnLoading.value = false
  }
}

async function handleQuickAddWatchlist(code) {
  quickWlLoading.value = code
  try {
    await addStockToWatchlist(code)
  } finally {
    quickWlLoading.value = ''
  }
}

function handleSearch() {
  const code = searchInput.value.trim()
  if (!code) {
    ElMessage.warning('请输入股票代码')
    return
  }
  // 提取6位数字代码
  const match = code.match(/\d{6}/)
  if (!match) {
    ElMessage.warning('请输入有效的6位股票代码')
    return
  }
  stockCode.value = match[0]
  router.replace(`/analysis/${stockCode.value}`)
  loadAllData()
}

function selectStock(code) {
  stockCode.value = code
  searchInput.value = code
  router.replace(`/analysis/${code}`)
  loadAllData()
}

// =========================================================================
// 监听路由变化
// =========================================================================
watch(() => route.params.code, (newCode) => {
  if (newCode) {
    stockCode.value = newCode
    searchInput.value = newCode
    loadAllData()
  }
}, { immediate: false })

// =========================================================================
// 生命周期
// =========================================================================
onMounted(() => {
  // 从路由参数获取初始股票代码
  if (route.params.code) {
    stockCode.value = route.params.code
    searchInput.value = route.params.code
    loadAllData()
  }
})
</script>

<style scoped>
.analysis-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* 搜索区域 */
.search-section {
  text-align: center;
  padding: 60px 20px;
}
.search-section h2 {
  font-size: 24px;
  margin-bottom: 8px;
}
.search-input {
  max-width: 500px;
  margin: 0 auto 20px;
}
.stock-examples {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}
.hot-stock-wrap {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.hot-add-wl {
  padding: 0 4px;
}
.example-label {
  color: #909399;
  font-size: 13px;
}
.example-tag {
  cursor: pointer;
}
.example-tag:hover {
  opacity: 0.8;
}

/* 股票头部 */
.stock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.header-info h2 {
  margin: 0;
  font-size: 20px;
}
.stock-code {
  font-size: 14px;
  color: #909399;
  font-weight: 400;
  margin-left: 8px;
}
.header-quote {
  text-align: center;
}
.quote-price {
  font-size: 28px;
  font-weight: 700;
  font-family: 'DIN', 'Helvetica Neue', monospace;
}
.quote-change {
  font-size: 16px;
  font-weight: 600;
}
.quote-change.up { color: #f56c6c; }
.quote-change.down { color: #1ecd94; }

/* 标签页 */
.analysis-tabs {
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* 图表：保证宽度参与布局，避免左侧画布被父级 clip */
.chart-tab-body {
  position: relative;
  min-height: 200px;
}
.chart-container {
  width: 100%;
  min-width: 280px;
  background: #fff;
  border-radius: 4px;
  padding: 8px 4px 8px 8px;
  overflow: visible;
}
.quote-detail {
  margin-top: 16px;
}

/* 财务卡片 */
.fin-card {
  text-align: center;
  margin-bottom: 16px;
}
.fin-card :deep(.el-card__body) {
  padding: 16px 12px;
}
.fin-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}
.fin-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  font-family: 'DIN', 'Helvetica Neue', monospace;
}

/* 公司概况（与上方财务卡片区间隔；fin-card 已有 margin-bottom） */
.profile-card {
  margin-top: 16px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
}
.profile-desc {
  width: 100%;
}
.profile-desc :deep(.el-descriptions__label) {
  width: 128px;
  white-space: nowrap;
}
.profile-desc :deep(.el-descriptions__content) {
  min-width: 0;
  word-break: break-word;
}
.profile-value {
  font-size: 13px;
  color: #606266;
  line-height: 1.75;
}

/* 十大股东 */
.holders-card {
  margin-top: 16px;
}
.holders-card :deep(.el-card__body) {
  padding-top: 8px;
}
.holders-table {
  min-width: 0;
}

/* 舆情 */
.sentiment-summary {
  margin-bottom: 16px;
}
.sent-card {
  margin-top: 16px;
}
.sent-card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
@media (min-width: 768px) {
  .sent-card-header {
    flex-direction: row;
    align-items: baseline;
    gap: 12px;
  }
}
.news-scroll {
  max-height: 500px;
  overflow-y: auto;
}
.sent-news-item {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}
.sent-news-item:hover {
  background: #f5f7fa;
}
.sent-news-item:last-child { border-bottom: none; }
.sent-news-title {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 6px;
}
.sent-news-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #c0c4cc;
  align-items: center;
}

/* AI报告 */
.report-section {
  min-height: 300px;
}
.report-generate {
  padding: 40px 0;
}
.report-loading {
  text-align: center;
  padding: 60px 0;
}
.report-loading p {
  margin: 12px 0 4px;
  font-size: 15px;
  color: #606266;
}
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.report-header h3 {
  margin: 0;
  font-size: 18px;
}
.report-body {
  font-size: 14px;
  line-height: 1.9;
  color: #303133;
  padding: 0 20px;
}
.report-body :deep(strong) {
  color: #409EFF;
}

/* 巴菲特评估 */
.buffett-section {
  min-height: 280px;
}
.buffett-top-tip-row {
  margin-bottom: 14px;
  padding: 12px 14px;
  background: #f5f7fa;
  border-radius: 8px;
}
.buffett-stream-wait {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px;
  color: #606266;
}
.buffett-stream-wrap {
  margin-top: 12px;
}
.buffett-stream-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.buffett-stream-pre {
  margin: 0;
  padding: 14px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: min(52vh, 520px);
  overflow-y: auto;
}
.buffett-stream-caret {
  animation: buffett-caret-blink 1s step-end infinite;
  color: #67c23a;
}
@keyframes buffett-caret-blink {
  50% { opacity: 0; }
}
.buffett-ai-wrap {
  margin-top: 20px;
  padding: 16px;
  background: #fafafa;
  border: 1px solid #e1f3d8;
  border-radius: 8px;
}
.buffett-ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}
.buffett-ai-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.buffett-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}
.buffett-ai-body :deep(h2) {
  color: #2d8f47;
}
.buffett-generate {
  padding: 40px 0;
}
.buffett-template-body {
  font-size: 14px;
  line-height: 1.9;
  color: #303133;
}
.buffett-template-body :deep(h2) {
  font-size: 18px;
  margin: 16px 0 10px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 6px;
}
.buffett-template-body :deep(h3) {
  font-size: 16px;
  margin: 14px 0 8px;
  color: #409eff;
}
.buffett-template-body :deep(h4),
.buffett-template-body :deep(h5) {
  font-size: 14px;
  margin: 10px 0 6px;
  color: #606266;
}
.buffett-template-body :deep(strong) {
  color: #67c23a;
}
.buffett-error-alert {
  margin-top: 16px;
}
</style>
