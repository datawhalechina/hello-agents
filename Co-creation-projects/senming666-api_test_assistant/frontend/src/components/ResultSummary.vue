<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>② 测试结果</span>
        <!-- 右上角：整体结论标签，颜色由通过率 computed 动态决定 -->
        <el-tag :type="rateLevel" effect="dark" size="large">
          {{ rateText }}
        </el-tag>
      </div>
    </template>

    <!-- 统计四宫格：el-row 栅格一行，el-col span=6 表示每块占 1/4 宽 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="item in statItems" :key="item.label">
        <div class="stat-item" :class="item.colorClass">
          <div class="stat-value">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 通过率进度条：percentage 是 0-100 的数字 -->
    <el-progress
      :percentage="percent"
      :status="progressStatus"
      :stroke-width="14"
    />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

// props：父组件把 summary 传进来，本组件只负责"读"和"算"，不修改它
const props = defineProps({
  summary: {
    type: Object,
    required: true, // required: true → 父组件必须传，漏传会告警
  },
})

// 通过率取整成百分比数字（后端给的是保留 1 位小数的数值）
const percent = computed(() => Math.round(props.summary.pass_rate ?? 0))

// 进度条三种状态色：绿(>=90) 橙(>=60) 红(<60)
const progressStatus = computed(() => {
  if (percent.value >= 90) return 'success'
  if (percent.value >= 60) return 'warning'
  return 'exception'
})

// 右上角标签的 Element 颜色类型
const rateLevel = computed(() => {
  if (percent.value >= 90) return 'success'
  if (percent.value >= 60) return 'warning'
  return 'danger'
})

// 标签文字
const rateText = computed(() => `通过率 ${percent.value}%`)

// 四张统计卡的数据（一个数组 = 一份数据源，模板 v-for 遍历生成，避免写四遍）
const statItems = computed(() => [
  { label: '总用例', value: props.summary.total ?? 0, colorClass: '' },
  { label: '通过', value: props.summary.passed ?? 0, colorClass: 'text-success' },
  { label: '失败', value: props.summary.failed ?? 0, colorClass: 'text-danger' },
  { label: '通过率', value: `${props.summary.pass_rate ?? 0}%`, colorClass: '' },
])
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between; /* 标题靠左、tag 靠右 */
  font-weight: 600;
  font-size: 16px;
}

.stat-row {
  margin-bottom: 4px;
}

.stat-item {
  text-align: center;
  padding: 14px 0;
  border-radius: 8px;
  background: #f7f8fa;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

/* 通过数用绿色、失败数用红色 */
.text-success .stat-value {
  color: #67c23a;
}

.text-danger .stat-value {
  color: #f56c6c;
}
</style>
