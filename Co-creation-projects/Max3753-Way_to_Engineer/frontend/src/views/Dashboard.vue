<template>
  <div class="dashboard-view">
    <div class="view-header">
      <div class="header-left">
        <h1>{{ langStore.t('dashboard.title') }}</h1>
        <p>{{ langStore.t('dashboard.subtitle') }}</p>
      </div>
      <div class="path-selector">
        <button
          v-for="path in pathOptions"
          :key="path.value"
          :class="['path-tab', { active: selectedPath === path.value }]"
          @click="switchPath(path.value)"
        >
          <span class="tab-icon">{{ path.icon }}</span>
          {{ path.label }}
        </button>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="card-icon total-tests">📋</div>
        <div class="card-body">
          <span class="card-value">{{ totalTests }}</span>
          <span class="card-label">{{ langStore.t('dashboard.totalTests') }}</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="card-icon avg-score">📊</div>
        <div class="card-body">
          <span class="card-value">{{ averageScore }}</span>
          <span class="card-label">{{ langStore.t('dashboard.avgScore') }}</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="card-icon current-level">🏆</div>
        <div class="card-body">
          <span class="card-value">{{ currentLevelText }}</span>
          <span class="card-label">{{ langStore.t('dashboard.currentLevel') }}</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="card-icon best-skill">⭐</div>
        <div class="card-body">
          <span class="card-value">{{ bestSkillName }}</span>
          <span class="card-label">{{ langStore.t('dashboard.bestSkill') }}</span>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <!-- 雷达图：分类水平 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>{{ langStore.t('dashboard.categoryLevels') }}</h3>
          <span v-if="latestAssessment" class="chart-meta">
            {{ langStore.t('dashboard.recentTest') }}{{ formatDate(latestAssessment.completed_at) }}
          </span>
        </div>
        <div v-if="latestAssessment && radarData" class="chart-container">
          <Radar :data="radarData" :options="radarOptions" />
        </div>
        <div v-else class="empty-chart">
          <span class="empty-icon">📡</span>
          <p>{{ langStore.t('dashboard.noTestData') }}</p>
          <button class="btn btn-primary btn-sm" @click="goToAssessment">{{ langStore.t('dashboard.startTest') }}</button>
        </div>
      </div>

      <!-- 折线图：成绩趋势 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>{{ langStore.t('dashboard.scoreTrend') }}</h3>
          <span v-if="assessments.length > 0" class="chart-meta">
            {{ langStore.t('dashboard.totalTestsCount', { count: assessments.length }) }}
          </span>
        </div>
        <div v-if="assessments.length >= 1" class="chart-container">
          <Line :data="trendData" :options="trendOptions" />
        </div>
        <div v-else class="empty-chart">
          <span class="empty-icon">📈</span>
          <p>{{ langStore.t('dashboard.trendDesc') }}</p>
        </div>
      </div>
    </div>

    <!-- 最近测试记录 -->
    <div class="recent-card">
      <div class="chart-header">
        <h3>{{ langStore.t('dashboard.recentRecords') }}</h3>
        <button
          v-if="assessments.length > 0"
          class="btn btn-outline btn-sm"
          @click="goToAssessment"
        >
          {{ langStore.t('dashboard.retake') }}
        </button>
      </div>
      <div v-if="assessments.length > 0" class="history-list">
        <div
          v-for="(item, index) in sortedAssessments"
          :key="index"
          class="history-item"
        >
          <div class="history-index">
            <span :class="['rank-badge', index === 0 ? 'top' : '']">{{ index + 1 }}</span>
          </div>
          <div class="history-info">
            <span class="history-date">{{ formatDate(item.completed_at) }}</span>
            <div class="history-categories">
              <span
                v-for="(score, cat) in item.category_scores"
                :key="cat"
                class="cat-tag"
              >
                {{ getCategoryName(String(cat)) }} {{ Math.round(score) }}%
              </span>
            </div>
          </div>
          <div class="history-score-area">
            <span :class="['score-pill', getScoreClass(item.score)]">{{ Math.round(item.score) }}</span>
            <span :class="['level-badge', item.level]">{{ getLevelText(item.level) }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-history">
        <span class="empty-icon">📭</span>
        <p>{{ langStore.t('dashboard.noRecords') }}</p>
        <button class="btn btn-primary btn-sm" @click="goToAssessment">{{ langStore.t('dashboard.firstTest') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { Radar, Line } from 'vue-chartjs'
import { useAuthStore } from '../stores/authStore'
import { useLangStore } from '../stores/langStore'
import {
  Chart as ChartJS,
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  LineController
} from 'chart.js'

ChartJS.register(
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  LineController
)

const router = useRouter()
const authStore = useAuthStore()
const langStore = useLangStore()

// --- Types ---
interface AssessmentRecord {
  path_type: string
  score: number
  level: string
  category_scores: Record<string, number>
  completed_at: string
}

// --- State ---
const selectedPath = ref('frontend')
const assessments = ref<AssessmentRecord[]>([])

const pathOptions = [
  { value: 'frontend', label: '前端开发', icon: '🎨' },
  { value: 'backend', label: '后端开发', icon: '⚙️' },
  { value: 'fullstack', label: '全栈开发', icon: '🚀' }
]

// --- Computed: Summary ---
const totalTests = computed(() => assessments.value.length)

const averageScore = computed(() => {
  if (assessments.value.length === 0) return '—'
  const sum = assessments.value.reduce((acc, a) => acc + a.score, 0)
  return Math.round(sum / assessments.value.length)
})

const currentLevelText = computed(() => {
  const latest = sortedAssessments.value[0]
  if (!latest) return '—'
  return getLevelText(latest.level)
})

const bestSkillName = computed(() => {
  const latest = sortedAssessments.value[0]
  if (!latest || !latest.category_scores) return '—'
  const entries = Object.entries(latest.category_scores)
  if (entries.length === 0) return '—'
  const best = entries.reduce((a, b) => (b[1] > a[1] ? b : a))
  return getCategoryName(best[0])
})

const latestAssessment = computed(() => {
  return sortedAssessments.value[0] || null
})

const sortedAssessments = computed(() => {
  return [...assessments.value].sort(
    (a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()
  )
})

// --- Computed: Radar Chart ---
const radarData = computed(() => {
  if (!latestAssessment.value) return null
  const scores = latestAssessment.value.category_scores
  const labels = Object.keys(scores).map((k) => getCategoryName(k))
  const values = Object.values(scores)

  return {
    labels,
    datasets: [
      {
        label: '技能水平',
        data: values,
        backgroundColor: 'rgba(102, 126, 234, 0.18)',
        borderColor: '#667eea',
        borderWidth: 2,
        pointBackgroundColor: '#667eea',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true
      }
    ]
  }
})

const radarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    r: {
      beginAtZero: true,
      max: 100,
      ticks: {
        stepSize: 20,
        display: true,
        color: '#999',
        backdropColor: 'transparent' as const,
        font: { size: 11 }
      },
      grid: {
        color: 'rgba(0, 0, 0, 0.06)'
      },
      angleLines: {
        color: 'rgba(0, 0, 0, 0.06)'
      },
      pointLabels: {
        color: '#333',
        font: { size: 13, weight: '500' as const }
      }
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(0,0,0,0.75)',
      titleFont: { size: 13 },
      bodyFont: { size: 12 },
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: (ctx: any) => `${ctx.label}: ${ctx.raw}%`
      }
    }
  }
}

// --- Computed: Trend Chart ---
const trendData = computed(() => {
  if (assessments.value.length === 0) return { labels: [], datasets: [] }
  const sorted = sortedAssessments.value

  return {
    labels: sorted.map((a) => formatDateShort(a.completed_at)),
    datasets: [
      {
        label: '测试得分',
        data: sorted.map((a) => a.score),
        borderColor: '#667eea',
        backgroundColor: (ctx: any) => {
          const chart = ctx.chart
          const { ctx: canvasCtx, chartArea } = chart
          if (!chartArea) return 'rgba(102, 126, 234, 0.1)'
          const gradient = canvasCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, 'rgba(102, 126, 234, 0.25)')
          gradient.addColorStop(1, 'rgba(102, 126, 234, 0.02)')
          return gradient
        },
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#667eea',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7
      }
    ]
  }
})

const trendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#999', font: { size: 12 } }
    },
    y: {
      beginAtZero: true,
      max: 100,
      grid: { color: 'rgba(0, 0, 0, 0.04)' },
      ticks: {
        color: '#999',
        stepSize: 20,
        font: { size: 12 },
        callback: (val: any) => `${val}分`
      }
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(0,0,0,0.75)',
      titleFont: { size: 13 },
      bodyFont: { size: 12 },
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: (ctx: any) => `得分: ${ctx.raw}分`
      }
    }
  }
}

// --- Methods ---
const fetchAssessments = async () => {
  try {
    const response = await axios.get(
      `/api/assessment/history/${selectedPath.value}`,
      { params: { user_id: authStore.userId } }
    )
    assessments.value = response.data.assessments || []
  } catch (error) {
    console.error('Failed to load assessment history:', error)
    assessments.value = []
  }
}

const switchPath = (path: string) => {
  selectedPath.value = path
  fetchAssessments()
}

const goToAssessment = () => {
  router.push({
    path: '/assessment',
    query: { path: selectedPath.value }
  })
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

const formatDateShort = (dateStr: string) => {
  const d = new Date(dateStr)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}

const getCategoryName = (category: string) => {
  const names: Record<string, string> = {
    html_css: 'HTML/CSS',
    javascript: 'JavaScript',
    vue: 'Vue.js',
    browser_apis: '浏览器API',
    python: 'Python',
    api_design: 'API设计',
    database: '数据库',
    system_design: '系统设计'
  }
  return names[category] || category
}

const getLevelText = (level: string) => {
  const texts: Record<string, string> = {
    beginner: '入门',
    intermediate: '中级',
    advanced: '高级'
  }
  return texts[level] || level
}

const getScoreClass = (score: number) => {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'fair'
  return 'poor'
}

// --- Lifecycle ---
onMounted(async () => {
  // 读取用户已选路径
  try {
    const progressRes = await axios.get('/api/learning/progress', {
      params: { user_id: authStore.userId }
    })
    if (progressRes.data.current_path) {
      selectedPath.value = progressRes.data.current_path
    }
  } catch (e) {
    // ignore, defaults to 'frontend'
  }
  fetchAssessments()
})

// 从keep-alive缓存恢复时刷新数据
onActivated(() => {
  fetchAssessments()
})
</script>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: #f8f9fa;
  overflow-y: auto;
}

/* Header */
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  background: white;
  border-bottom: 1px solid #e5e5e5;
}

.view-header h1 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #1a1a1a;
}

.view-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.path-selector {
  display: flex;
  gap: 6px;
  background: #f5f5f5;
  border-radius: 12px;
  padding: 4px;
}

.path-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.path-tab:hover {
  color: #333;
  background: rgba(255, 255, 255, 0.6);
}

.path-tab.active {
  background: white;
  color: #667eea;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.tab-icon {
  font-size: 15px;
}

/* Summary Cards */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 24px 32px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.card-icon.total-tests {
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
}

.card-icon.avg-score {
  background: linear-gradient(135deg, #f0f5ff 0%, #d6e4ff 100%);
}

.card-icon.current-level {
  background: linear-gradient(135deg, #fff7e6 0%, #ffe7ba 100%);
}

.card-icon.best-skill {
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.2;
}

.card-label {
  font-size: 13px;
  color: #999;
}

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 0 32px;
  margin-bottom: 16px;
}

.chart-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1a1a1a;
}

.chart-meta {
  font-size: 12px;
  color: #999;
}

.chart-container {
  height: 280px;
  position: relative;
}

.empty-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 240px;
  gap: 8px;
}

.empty-icon {
  font-size: 40px;
  opacity: 0.5;
}

.empty-chart p {
  margin: 0;
  color: #999;
  font-size: 14px;
  text-align: center;
}

/* Recent Assessments */
.recent-card {
  margin: 0 32px 24px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: #f8f9fa;
  border-radius: 10px;
  transition: background 0.15s;
}

.history-item:hover {
  background: #f0f0f0;
}

.rank-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #999;
  background: #e8e8e8;
  flex-shrink: 0;
}

.rank-badge.top {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.history-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.history-date {
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.history-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.cat-tag {
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 6px;
  font-size: 11px;
  color: #666;
  white-space: nowrap;
}

.history-score-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.score-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
}

.score-pill.excellent {
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  color: #389e0d;
}

.score-pill.good {
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
  color: #0958d9;
}

.score-pill.fair {
  background: linear-gradient(135deg, #fff7e6 0%, #ffd591 100%);
  color: #d46b08;
}

.score-pill.poor {
  background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%);
  color: #cf1322;
}

.level-badge {
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.level-badge.beginner {
  background: #f6ffed;
  color: #52c41a;
}

.level-badge.intermediate {
  background: #e6f7ff;
  color: #1890ff;
}

.level-badge.advanced {
  background: #fff2f0;
  color: #ff4d4f;
}

/* Empty History */
.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 8px;
}

.empty-history p {
  margin: 0;
  color: #999;
  font-size: 14px;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-outline {
  background: white;
  border: 1px solid #d9d9d9;
  color: #666;
}

.btn-outline:hover {
  border-color: #667eea;
  color: #667eea;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}

/* Responsive */
@media (max-width: 1024px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .view-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .summary-cards {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .charts-row {
    padding: 0 16px;
  }

  .recent-card {
    margin: 0 16px 16px;
  }

  .history-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
