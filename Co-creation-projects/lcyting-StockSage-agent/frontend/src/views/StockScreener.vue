<template>
  <div class="screener-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>智能选股</h2>
      <el-text type="info">多条件股票筛选，自然语言驱动的智能选股引擎</el-text>
    </div>

    <!-- 筛选面板 -->
    <el-card shadow="hover" class="filter-panel">
      <!-- 自然语言查询输入 -->
      <div class="query-row">
        <el-input
          v-model="query"
          placeholder="输入选股条件，如：市盈率小于20且ROE大于15%的A股"
          size="large"
          clearable
          class="query-input"
          @keyup.enter="handleSearch"
        >
          <template #prepend>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button
              type="primary"
              :loading="searching"
              :icon="Search"
              @click="handleSearch"
            >
              筛选
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 快捷条件标签 -->
      <div class="quick-tags" v-if="conditions">
        <span class="tags-label">快捷条件：</span>
        <el-tag
          v-for="cat in conditions.categories"
          :key="cat.name"
          class="quick-tag"
          type="info"
          @click="showExamples(cat)"
        >
          {{ cat.name }}
        </el-tag>
      </div>

      <!-- 条件参考展开区 -->
      <el-collapse v-if="showRef" v-model="activeRefs" class="ref-collapse">
        <el-collapse-item
          v-for="cat in conditions?.categories"
          :key="cat.name"
          :title="cat.name"
          :name="cat.name"
        >
          <el-text type="info" size="small">{{ cat.description }}</el-text>
          <div class="example-list">
            <el-tag
              v-for="ex in cat.examples"
              :key="ex"
              class="example-tag"
              @click="applyExample(ex)"
            >
              {{ ex }}
            </el-tag>
          </div>
        </el-collapse-item>
      </el-collapse>

      <el-button
        type="primary"
        link
        size="small"
        class="toggle-ref"
        @click="showRef = !showRef"
      >
        <el-icon><ArrowDown v-if="!showRef" /><ArrowUp v-else /></el-icon>
        {{ showRef ? '收起' : '展开' }}条件参考
      </el-button>
    </el-card>

    <!-- 筛选结果 -->
    <el-card shadow="hover" class="result-panel" v-loading="searching">
      <template #header>
        <div class="result-header">
          <span class="card-title">
            筛选结果
            <template v-if="results.total_count > 0">
              （共 {{ results.total_count }} 只）
            </template>
          </span>
          <el-button
            v-if="selectedStocks.length > 0"
            type="primary"
            size="small"
            @click="showCompare = true"
          >
            对比选中（{{ selectedStocks.length }}）
          </el-button>
        </div>
      </template>

      <!-- 筛选条件概览 -->
      <div v-if="results.conditions.length > 0" class="condition-summary">
        <el-tag
          v-for="(cond, i) in results.conditions"
          :key="i"
          type="success"
          effect="plain"
          class="cond-tag"
        >
          {{ cond.describe || cond.stock_count }} 只
        </el-tag>
      </div>

      <!-- 结果表格 -->
      <el-table
        v-if="results.stocks.length > 0"
        :data="results.stocks"
        stripe
        @selection-change="handleSelectionChange"
        max-height="500"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column
          v-for="col in resultColumns"
          :key="col"
          :prop="col"
          :label="col"
          :min-width="100"
          sortable
        />
        <el-table-column label="操作" width="168" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              @click="goToAnalysis(row)"
            >
              分析
            </el-button>
            <el-button
              type="warning"
              link
              size="small"
              :loading="Boolean(wlAdding[pickScreenerStockCode(row)])"
              @click="handleAddWatchlistRow(row)"
            >
              加自选
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-else-if="!searching"
        description="输入条件开始筛选"
        :image-size="80"
      />
    </el-card>

    <!-- 多股对比弹窗 -->
    <el-dialog
      v-model="showCompare"
      title="多股对比"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <el-table
        :data="compareData"
        border
        stripe
        v-if="selectedStocks.length > 0"
      >
        <el-table-column prop="field" label="指标" width="120" fixed />
        <el-table-column
          v-for="stock in selectedStocks"
          :key="stock.股票代码 || stock.代码"
          :label="stock.股票名称 || stock.名称 || stock.股票代码 || '--'"
        >
          <template #default="{ row }">
            {{ row[stock.股票代码 || stock.代码] ?? '--' }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'StockScreener' }
</script>

<script setup>
/**
 * 智能选股页面
 *
 * 支持自然语言选股条件输入，快捷标签，条件参考，结果展示与多股对比。
 * 数据来源：后端 /api/v1/screener
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import {
  addStockToWatchlist,
  pickScreenerStockCode,
} from '@/utils/watchlist'

const router = useRouter()

// =========================================================================
// 状态
// =========================================================================
const query = ref('')
const searching = ref(false)
const showRef = ref(false)
const activeRefs = ref([])
const showCompare = ref(false)

const conditions = ref(null)
const results = ref({ stocks: [], conditions: [], total_count: 0 })
const selectedStocks = ref([])
/** 选股表格「加自选」逐行 loading：key 为股票代码 */
const wlAdding = ref({})

// =========================================================================
// 计算属性
// =========================================================================

/** 从结果中提取表格列名 */
const resultColumns = computed(() => {
  if (results.value.stocks.length === 0) return []
  // 使用第一只股票的所有key作为列
  return Object.keys(results.value.stocks[0])
})

/** 将选中的股票转换为对比表格数据 */
const compareData = computed(() => {
  if (selectedStocks.value.length === 0) return []
  // 收集所有可能的字段
  const allFields = new Set()
  const stockMap = {}
  for (const stock of selectedStocks.value) {
    const code = stock['股票代码'] || stock['代码'] || ''
    stockMap[code] = stock
    Object.keys(stock).forEach(k => allFields.add(k))
  }
  // 构建行数据
  return Array.from(allFields).map(field => {
    const row = { field }
    for (const stock of selectedStocks.value) {
      const code = stock['股票代码'] || stock['代码'] || ''
      row[code] = stock[field] ?? '--'
    }
    return row
  })
})

// =========================================================================
// 方法
// =========================================================================

/** 加载可用的筛选条件参考 */
async function loadConditions() {
  try {
    const res = await api.get('/screener/conditions')
    if (res.code === 0 && res.data) {
      conditions.value = res.data
    }
  } catch (e) {
    console.error('加载筛选条件失败:', e)
  }
}

/** 执行选股 */
async function handleSearch() {
  const q = query.value.trim()
  if (!q) {
    ElMessage.warning('请输入选股条件')
    return
  }

  searching.value = true
  results.value = { stocks: [], conditions: [], total_count: 0 }
  selectedStocks.value = []

  try {
    const res = await api.post('/screener/search', null, {
      params: { query: q },
    })
    if (res.code === 0 && res.data) {
      results.value = {
        stocks: res.data.stocks || [],
        conditions: res.data.conditions || [],
        total_count: res.data.total_count || 0,
      }
      if (results.value.total_count === 0) {
        ElMessage.info('未找到符合条件的股票')
      } else {
        ElMessage.success(`筛选完成，共 ${results.value.total_count} 只股票`)
      }
    } else {
      ElMessage.error(res.message || '选股失败')
    }
  } catch (e) {
    ElMessage.error('选股请求失败: ' + (e.message || '未知错误'))
  } finally {
    searching.value = false
  }
}

/** 应用快捷条件示例 */
function applyExample(example) {
  query.value = example
  handleSearch()
}

/** 展开某类条件参考 */
function showExamples(cat) {
  showRef.value = true
  activeRefs.value = [cat.name]
}

/** 表格选中变化 */
function handleSelectionChange(selection) {
  selectedStocks.value = selection
}

/** 跳转到分析页面 */
function goToAnalysis(row) {
  const code = pickScreenerStockCode(row)
  if (code) {
    router.push(`/analysis/${code}`)
  }
}

/** 将选股结果加入妙想自选股 */
async function handleAddWatchlistRow(row) {
  let input = pickScreenerStockCode(row)
  if (!input) {
    input = String(row['股票名称'] ?? row['名称'] ?? '').trim()
  }
  if (!input) {
    ElMessage.warning('无法识别该股票的代码或名称')
    return
  }
  wlAdding.value = { ...wlAdding.value, [input]: true }
  try {
    await addStockToWatchlist(input)
  } finally {
    const next = { ...wlAdding.value }
    delete next[input]
    wlAdding.value = next
  }
}

// =========================================================================
// 生命周期
// =========================================================================
onMounted(() => {
  loadConditions()
})
</script>

<style scoped>
.screener-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
}

/* 筛选面板 */
.filter-panel {
  margin-bottom: 16px;
}

.query-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.query-input {
  flex: 1;
}

.quick-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.tags-label {
  font-size: 12px;
  color: #909399;
}
.quick-tag {
  cursor: pointer;
}
.quick-tag:hover {
  opacity: 0.8;
}

.ref-collapse {
  margin-top: 12px;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.example-tag {
  cursor: pointer;
  font-size: 12px;
}
.example-tag:hover {
  color: #409EFF;
  border-color: #409EFF;
}

.toggle-ref {
  margin-top: 8px;
}

/* 结果面板 */
.result-panel {
  min-height: 200px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.condition-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.cond-tag {
  cursor: default;
}
</style>
