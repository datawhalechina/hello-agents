<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const metricTypes = [
  { label: '体重 (kg)', value: 'weight' },
  { label: '睡眠时长 (h)', value: 'sleep_hours' },
  { label: '心率 (bpm)', value: 'heart_rate' },
  { label: '步数', value: 'steps' },
  { label: '体脂率 (%)', value: 'body_fat' },
  { label: '饮水量 (ml)', value: 'water_ml' },
]

const metric = ref('weight')
const days = ref(30)
const records = ref([])
const loading = ref(false)
const chartRef = ref(null)
let chart = null

function renderChart(points, unit) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 24, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: points.map((point) => point.date) },
      yAxis: { type: 'value', name: unit || '' },
      series: [
        {
          type: 'line',
          smooth: true,
          showSymbol: true,
          areaStyle: { opacity: 0.12 },
          data: points.map((point) => point.value),
        },
      ],
    },
    true,
  )
}

async function loadData() {
  loading.value = true
  try {
    const [trend, list] = await Promise.all([
      api.trends(metric.value, days.value),
      api.records(metric.value, days.value),
    ])
    records.value = list
    renderChart(trend.points || [], trend.unit)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>指标趋势</h2>
      <p>查看健康台账记录与按日期聚合的趋势图，数据来自对话中保存的健康记录。</p>
    </div>

    <div class="toolbar">
      <el-select v-model="metric" style="width: 180px">
        <el-option
          v-for="item in metricTypes"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-input-number v-model="days" :min="1" :max="3650" />
      <span class="muted">天</span>
      <el-button type="primary" :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <el-card shadow="never" style="margin-bottom: 16px">
      <div ref="chartRef" style="height: 320px" />
      <div v-if="!records.length && !loading" class="muted" style="text-align: center">
        暂无该指标记录，可在「健康对话」中录入。
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>最近记录（{{ records.length }} 条）</template>
      <el-table :data="records" size="small" empty-text="暂无记录">
        <el-table-column prop="recorded_at" label="记录时间" min-width="200" />
        <el-table-column prop="metric_type" label="指标" width="140" />
        <el-table-column prop="value" label="数值" width="120" />
        <el-table-column prop="unit" label="单位" width="100" />
        <el-table-column prop="note" label="备注" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>
