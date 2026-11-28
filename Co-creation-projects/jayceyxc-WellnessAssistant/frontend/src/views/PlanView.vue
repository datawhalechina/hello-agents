<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const plan = ref(null)
const versions = ref([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const current = await api.currentPlan()
    plan.value = current
    versions.value = current ? await api.planVersions(current.plan_id) : []
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>运动计划</h2>
      <p>当前生效的运动计划及其历史版本，每次身体反馈调整都会生成新版本。</p>
    </div>

    <div class="toolbar">
      <el-button type="primary" :loading="loading" @click="loadData">刷新</el-button>
      <span class="muted" v-if="plan">当前版本：v{{ plan.version }}</span>
    </div>

    <el-empty v-if="!plan && !loading" description="暂无运动计划，可在健康对话中生成" />

    <template v-if="plan">
      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <strong>{{ plan.goal || '未设置目标' }}</strong>
            <el-tag type="success">{{ plan.status }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="频率">{{ plan.content.frequency }}</el-descriptions-item>
          <el-descriptions-item label="单次时长">{{ plan.content.session_minutes }} 分钟</el-descriptions-item>
          <el-descriptions-item label="强度">{{ plan.content.intensity }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ plan.created_at }}</el-descriptions-item>
          <el-descriptions-item label="版本">v{{ plan.version }}</el-descriptions-item>
          <el-descriptions-item label="调整原因">{{ plan.reason }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 18px 0 8px">训练安排</h4>
        <el-table :data="plan.content.sessions || []" size="small">
          <el-table-column prop="type" label="运动类型" min-width="180" />
          <el-table-column prop="minutes" label="时长（分钟）" width="140" />
          <el-table-column prop="intensity" label="强度" width="120" />
        </el-table>

        <h4 style="margin: 18px 0 8px">注意事项</h4>
        <ul class="muted">
          <li v-for="(item, index) in plan.content.precautions || []" :key="index">{{ item }}</li>
        </ul>
        <p class="muted">进阶规则：{{ plan.content.progression }}</p>
      </el-card>

      <el-card shadow="never">
        <template #header>版本历史（{{ versions.length }} 个版本）</template>
        <el-table :data="versions" size="small">
          <el-table-column prop="version" label="版本" width="90" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="调整原因" min-width="240" />
          <el-table-column prop="created_at" label="创建时间" width="200" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>
