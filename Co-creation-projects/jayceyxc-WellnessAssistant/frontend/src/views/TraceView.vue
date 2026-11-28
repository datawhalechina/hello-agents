<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const traceId = ref(route.query.id || '')
const detail = ref(null)
const loading = ref(false)

function pretty(value) {
  return value ? JSON.stringify(value, null, 2) : ''
}

async function loadData() {
  const id = String(traceId.value || '').trim()
  if (!id) {
    ElMessage.warning('请输入 Trace ID')
    return
  }
  loading.value = true
  try {
    detail.value = await api.trace(id)
  } catch (error) {
    detail.value = null
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query.id,
  (id) => {
    if (id) {
      traceId.value = id
      loadData()
    }
  },
)

onMounted(() => {
  if (traceId.value) loadData()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Agent 调用链路</h2>
      <p>查看单次对话的思考、工具调用、工具结果与最终回复。对话页点击「查看调用链路」可自动跳转。</p>
    </div>

    <div class="toolbar">
      <el-input v-model="traceId" placeholder="Trace ID" style="width: 340px" @keydown.enter="loadData" />
      <el-button type="primary" :loading="loading" @click="loadData">查询</el-button>
    </div>

    <el-empty v-if="!detail && !loading" description="暂无链路数据" />

    <template v-if="detail">
      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>
          <div style="display: flex; justify-content: space-between">
            <strong>{{ detail.id }}</strong>
            <el-tag :type="detail.status === 'success' ? 'success' : 'danger'">{{ detail.status }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="会话 ID">{{ detail.session_id }}</el-descriptions-item>
          <el-descriptions-item label="步骤数">{{ detail.steps.length }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ detail.started_at }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ detail.ended_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户输入" :span="2">{{ detail.user_input }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>调用步骤</template>
        <el-timeline>
          <el-timeline-item
            v-for="step in detail.steps"
            :key="step.id"
            :timestamp="`步骤 ${step.step_no} · ${step.created_at}`"
            placement="top"
          >
            <el-card shadow="never">
              <div style="margin-bottom: 8px">
                <el-tag size="small">{{ step.step_type }}</el-tag>
                <el-tag v-if="step.tool_name" size="small" type="warning" style="margin-left: 8px">
                  {{ step.tool_name }}
                </el-tag>
                <span v-if="step.latency_ms !== null" class="muted" style="margin-left: 8px">
                  {{ step.latency_ms }} ms
                </span>
              </div>
              <div v-if="step.thought">{{ step.thought }}</div>
              <div v-if="step.tool_input"><strong>工具参数</strong><pre>{{ pretty(step.tool_input) }}</pre></div>
              <div v-if="step.tool_output"><strong>工具结果</strong><pre>{{ pretty(step.tool_output) }}</pre></div>
              <div v-if="step.error" style="color: #dc2626">{{ step.error }}</div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </el-card>

      <el-card shadow="never">
        <template #header>最终回复</template>
        <div style="white-space: pre-wrap; line-height: 1.7">{{ detail.final_answer }}</div>
      </el-card>
    </template>
  </div>
</template>
