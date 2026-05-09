<template>
  <div class="news-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>新闻舆情</h2>
      <el-text type="info">金融资讯聚合 · 个股舆情分析 · 情感研判</el-text>
    </div>

    <!-- 搜索 + 标签切换 -->
    <el-card shadow="hover" class="search-card">
      <div class="search-row">
        <el-input
          v-model="searchQuery"
          placeholder="搜索金融资讯，如：人工智能板块近期新闻"
          size="large"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #prepend>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button type="primary" :loading="loading" @click="handleSearch">
              搜索
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 子标签：热门 / 搜索 / 个股舆情 -->
      <el-tabs v-model="activeMode" class="news-tabs" @tab-change="handleModeChange">
        <el-tab-pane label="热门资讯" name="hot">
          <el-text type="info" size="small">今日A股市场热点动态、北向资金流向</el-text>
        </el-tab-pane>
        <el-tab-pane label="资讯搜索" name="search">
          <el-text type="info" size="small">按关键词搜索新闻、研报、公告</el-text>
        </el-tab-pane>
        <el-tab-pane label="个股舆情" name="sentiment">
          <div class="sentiment-input-row">
            <el-input
              v-model="sentimentCode"
              placeholder="输入6位股票代码，如 600519"
              size="small"
              class="sent-code-input"
              clearable
              @keyup.enter="handleSentiment"
            >
              <template #prepend>股票代码</template>
            </el-input>
            <el-button
              type="primary"
              size="small"
              :loading="sentLoading"
              @click="handleSentiment"
            >
              分析舆情
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 内容区 -->
    <el-row :gutter="16" class="content-row">
      <!-- 左侧：资讯列表 -->
      <el-col :span="16">
        <el-card shadow="hover" v-loading="loading || sentLoading">
          <template #header>
            <div class="card-header">
              <div class="card-title-block">
                <span class="card-title">
                  {{ activeMode === 'sentiment' ? `个股舆情 — ${sentimentCode || ''}` : '资讯列表' }}
                  <template v-if="newsTotal > 0">
                    <el-tag size="small" style="margin-left:8px;">共 {{ newsTotal }} 条</el-tag>
                  </template>
                </span>
                <el-text v-if="newsTotal > 0" size="small" type="info">点击条目查看全文</el-text>
              </div>

              <!-- 类型筛选 -->
              <el-radio-group
                v-model="typeFilter"
                size="small"
                @change="applyFilter"
              >
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="新闻">新闻</el-radio-button>
                <el-radio-button value="研报">研报</el-radio-button>
                <el-radio-button value="公告">公告</el-radio-button>
                <el-radio-button value="其他">其他</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <!-- 新闻列表 -->
          <div v-if="filteredNews.length > 0" class="news-scroll-list">
            <div
              v-for="(item, idx) in filteredNews"
              :key="idx"
              class="news-list-item"
              role="button"
              tabindex="0"
              @click="openNewsDetail(item)"
              @keyup.enter="openNewsDetail(item)"
            >
              <div class="item-title">
                <el-tag
                  size="small"
                  :type="
                    item.info_type === 'REPORT' || item.info_type_cn === '研报'
                      ? 'warning'
                      : item.info_type === 'ANNOUNCEMENT' || item.info_type_cn === '公告'
                        ? ''
                        : item.info_type === 'OTHER' || item.info_type_cn === '其他'
                          ? 'info'
                          : 'success'
                  "
                  effect="plain"
                >
                  {{ item.info_type_cn || item.info_type || '资讯' }}
                </el-tag>
                <span>{{ item.title }}</span>
              </div>
              <div class="item-content" v-if="item.content">
                {{ item.content }}
              </div>
              <div class="item-meta">
                <span class="item-date">{{ item.date }}</span>
                <span v-if="item.institution">{{ item.institution }}</span>
                <span v-if="item.entity_name">{{ item.entity_name }}</span>
                <span v-if="item.rating" class="item-rating">
                  <el-tag size="small" type="warning">{{ item.rating }}</el-tag>
                </span>
              </div>
            </div>
          </div>

          <el-empty
            v-else-if="!loading && !sentLoading"
            :description="activeMode === 'sentiment' ? '输入股票代码查看舆情' : activeMode === 'search' ? '输入关键词搜索资讯' : '点击加载热门资讯'"
            :image-size="60"
          >
            <el-button
              v-if="activeMode === 'hot'"
              type="primary"
              @click="loadHotNews"
            >
              加载热门资讯
            </el-button>
          </el-empty>
        </el-card>
      </el-col>

      <!-- 右侧：舆情统计图表 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">资讯类型分布</span>
          </template>
          <div v-if="newsTotal > 0" class="chart-wrapper">
            <v-chart :option="pieOption" autoresize style="height: 240px;" />
            <div class="chart-stats">
              <div class="stat-item">
                <span class="stat-dot news-dot"></span>
                新闻 {{ typeCounts['新闻'] || 0 }}
              </div>
              <div class="stat-item">
                <span class="stat-dot report-dot"></span>
                研报 {{ typeCounts['研报'] || 0 }}
              </div>
              <div class="stat-item">
                <span class="stat-dot announce-dot"></span>
                公告 {{ typeCounts['公告'] || 0 }}
              </div>
              <div v-if="(typeCounts['其他'] || 0) > 0" class="stat-item">
                <span class="stat-dot other-dot"></span>
                其他 {{ typeCounts['其他'] }}
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="60" />

          <!-- 舆情子分类（个股舆情模式下展示） -->
          <template v-if="activeMode === 'sentiment' && sentimentResult">
            <el-divider />
            <div class="sentiment-stats">
              <el-statistic title="新闻" :value="sentimentResult.news_items?.length || 0" />
              <el-statistic title="研报" :value="sentimentResult.report_items?.length || 0" />
              <el-statistic title="公告" :value="sentimentResult.announce_items?.length || 0" />
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <NewsDetailDrawer v-model="newsDrawerVisible" :item="newsDetailItem" />
  </div>
</template>

<script>
export default { name: 'NewsCenter' }
</script>

<script setup>
/**
 * 新闻舆情页面
 *
 * 提供金融资讯搜索、热门资讯浏览、个股舆情分析功能。
 * 数据来源：后端 /api/v1/news
 */
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import NewsDetailDrawer from '@/components/NewsDetailDrawer.vue'

// =========================================================================
// ECharts 引用
// =========================================================================
import VChart from 'vue-echarts'

// =========================================================================
// 状态
// =========================================================================
const activeMode = ref('hot')       // hot | search | sentiment
const loading = ref(false)
const sentLoading = ref(false)

// 搜索模式
const searchQuery = ref('')
const searchResults = ref([])

// 热门模式
const hotResults = ref([])

// 个股舆情模式
const sentimentCode = ref('')
const sentimentResult = ref(null)

// 类型筛选
const typeFilter = ref('all')

// 资讯全文抽屉（列表内为摘要，点击查看完整正文）
const newsDrawerVisible = ref(false)
const newsDetailItem = ref(null)

function openNewsDetail(item) {
  newsDetailItem.value = item
  newsDrawerVisible.value = true
}

// =========================================================================
// 计算属性
// =========================================================================

/** 当前模式下的所有新闻数据 */
const currentNews = computed(() => {
  if (activeMode.value === 'hot') return hotResults.value
  if (activeMode.value === 'search') return searchResults.value
  if (activeMode.value === 'sentiment') {
    if (!sentimentResult.value) return []
    return [
      ...(sentimentResult.value.news_items || []),
      ...(sentimentResult.value.report_items || []),
      ...(sentimentResult.value.announce_items || []),
    ]
  }
  return []
})

/** 按类型筛选后的新闻 */
const filteredNews = computed(() => {
  if (typeFilter.value === 'all') return currentNews.value
  const filterMap = {
    '新闻': 'NEWS',
    '研报': 'REPORT',
    '公告': 'ANNOUNCEMENT',
    '其他': 'OTHER',
  }
  const targetType = filterMap[typeFilter.value]
  return currentNews.value.filter(
    (item) =>
      item.info_type === targetType ||
      item.info_type_cn === typeFilter.value,
  )
})

/** 总数量 */
const newsTotal = computed(() => currentNews.value.length)

/** 各类型计数（优先读后端 info_type，与饼图一致） */
const typeCounts = computed(() => {
  const counts = { 新闻: 0, 研报: 0, 公告: 0, 其他: 0 }
  for (const item of currentNews.value) {
    const en = String(item.info_type || '').toUpperCase()
    if (en === 'REPORT') counts['研报'] += 1
    else if (en === 'ANNOUNCEMENT') counts['公告'] += 1
    else if (en === 'NEWS') counts['新闻'] += 1
    else counts['其他'] += 1
  }
  return counts
})

/** 饼图配置 */
const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      name: '资讯类型',
      type: 'pie',
      // 略收紧环形尺寸，避免窄栏内左侧标签/图形贴边被裁切
      radius: ['36%', '62%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' },
      },
      data: [
        { value: typeCounts.value['新闻'], name: '新闻', itemStyle: { color: '#67c23a' } },
        { value: typeCounts.value['研报'], name: '研报', itemStyle: { color: '#e6a23c' } },
        { value: typeCounts.value['公告'], name: '公告', itemStyle: { color: '#909399' } },
        { value: typeCounts.value['其他'], name: '其他', itemStyle: { color: '#409eff' } },
      ].filter(d => d.value > 0),
    },
  ],
}))

// =========================================================================
// 方法
// =========================================================================

/** 加载热门资讯 */
async function loadHotNews() {
  loading.value = true
  try {
    const res = await api.get('/news/hot')
    if (res.code === 0 && res.data?.items) {
      hotResults.value = res.data.items
      ElMessage.success(`加载了 ${hotResults.value.length} 条热门资讯`)
    } else {
      ElMessage.error(res.message || '加载热门资讯失败')
    }
  } catch (e) {
    ElMessage.error('加载热门资讯失败')
  } finally {
    loading.value = false
  }
}

/** 搜索资讯 */
async function handleSearch() {
  const q = searchQuery.value.trim()
  if (!q) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  activeMode.value = 'search'
  loading.value = true
  try {
    const res = await api.get('/news/search', { params: { query: q } })
    if (res.code === 0 && res.data?.items) {
      searchResults.value = res.data.items
      ElMessage.success(`找到 ${searchResults.value.length} 条相关资讯`)
    } else {
      ElMessage.error(res.message || '搜索失败')
    }
  } catch (e) {
    ElMessage.error('搜索请求失败')
  } finally {
    loading.value = false
  }
}

/** 个股舆情分析 */
async function handleSentiment() {
  const code = sentimentCode.value.trim()
  if (!code || code.length < 4) {
    ElMessage.warning('请输入有效的股票代码')
    return
  }
  sentLoading.value = true
  sentimentResult.value = null
  try {
    const res = await api.get(`/news/sentiment/${code}`)
    if (res.code === 0 && res.data) {
      sentimentResult.value = res.data
      const total = (res.data.news_items?.length || 0) + (res.data.report_items?.length || 0) + (res.data.announce_items?.length || 0)
      ElMessage.success(`舆情分析完成，共 ${total} 条相关资讯`)
    } else {
      ElMessage.error(res.message || '舆情分析失败')
    }
  } catch (e) {
    ElMessage.error('舆情分析请求失败')
  } finally {
    sentLoading.value = false
  }
}

/** 模式切换 */
function handleModeChange(mode) {
  typeFilter.value = 'all'
  if (mode === 'hot' && hotResults.value.length === 0) {
    loadHotNews()
  }
}

/** 类型筛选 */
function applyFilter() {
  // filteredNews 是计算属性，自动更新
}

// =========================================================================
// 生命周期
// =========================================================================
onMounted(() => {
  // 默认加载热门资讯
  loadHotNews()
})
</script>

<style scoped>
.news-page {
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

/* 搜索卡片 */
.search-card {
  margin-bottom: 16px;
}
.search-row {
  display: flex;
  gap: 12px;
}
.search-input {
  flex: 1;
}

.news-tabs {
  margin-top: 8px;
}

.sentiment-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.sent-code-input {
  width: 220px;
}

/* 内容区 */
.content-row {
  align-items: flex-start;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
}
.card-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
@media (min-width: 900px) {
  .card-title-block {
    flex-direction: row;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 10px;
  }
}

/* 新闻列表 */
.news-scroll-list {
  max-height: 600px;
  overflow-y: auto;
}
.news-list-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}
.news-list-item:last-child {
  border-bottom: none;
}
.news-list-item:hover {
  background: #f5f7fa;
}
.item-title {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  line-height: 1.5;
}
.item-content {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.item-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  font-size: 11px;
  color: #c0c4cc;
  align-items: center;
}
.item-rating {
  margin-left: auto;
}

/* 图表区：两侧留白，防止环形图在卡片内左侧显示不全 */
.chart-wrapper {
  width: 100%;
  padding: 8px 12px;
  box-sizing: border-box;
  overflow: visible;
}
.chart-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  margin-top: 8px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}
.stat-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.news-dot { background: #67c23a; }
.report-dot { background: #e6a23c; }
.announce-dot { background: #909399; }
.other-dot { background: #409eff; }

.sentiment-stats {
  display: flex;
  justify-content: space-around;
}
</style>
