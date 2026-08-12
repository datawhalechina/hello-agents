<template>
  <div class="ai-analysis-panel">
    <div v-if="!started" class="start-section">
      <p class="desc">{{ description }}</p>
      <el-button
        :type="buttonType"
        size="large"
        :loading="isStreaming"
        @click="startAnalysis"
        :icon="buttonIcon"
      >
        {{ buttonLabel }}
      </el-button>
    </div>

    <StreamOutput
      v-else
      :content="content"
      :statusText="statusText"
      :emotionalText="emotionalText"
      :metaInfo="metaInfo"
      :isStreaming="isStreaming"
      :error="error"
      @save="saveToHistory"
      @download="downloadReport"
      @clear="clearAnalysis"
    />

    <el-button
      v-if="started && !isStreaming"
      type="primary"
      style="margin-top: 12px;"
      @click="startAnalysis"
    >
      重新生成
    </el-button>

    <el-button
      v-if="started"
      style="margin-top: 12px; margin-left: 8px;"
      @click="showHistory"
    >
      <el-icon><Clock /></el-icon> 历史记录
    </el-button>

    <HistoryDrawer
      v-model:visible="historyVisible"
      :type="historyType"
    />
  </div>
</template>

<script>
export default { name: 'AIAnalysisPanel' }
</script>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import StreamOutput from './StreamOutput.vue'
import HistoryDrawer from './HistoryDrawer.vue'

const props = defineProps({
  stockCode: { type: String, default: '' },
  stockName: { type: String, default: '' },
  apiEndpoint: { type: String, required: true },
  historyType: { type: String, required: true },
  buttonLabel: { type: String, default: '开始AI分析' },
  buttonType: { type: String, default: 'primary' },
  buttonIcon: { type: String, default: '' },
  description: { type: String, default: '点击按钮启动AI自动分析' },
})

const started = ref(false)
const isStreaming = ref(false)
const content = ref('')
const statusText = ref('')
const emotionalText = ref('')
const metaInfo = ref(null)
const error = ref('')
const historyVisible = ref(false)

async function startAnalysis() {
  if (!props.stockCode) {
    ElMessage.warning('请先选择一只股票')
    return
  }

  started.value = true
  isStreaming.value = true
  content.value = ''
  statusText.value = ''
  emotionalText.value = ''
  error.value = ''
  metaInfo.value = null

  try {
    const response = await fetch(`/api/v1${props.apiEndpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_code: props.stockCode,
        stock_name: props.stockName,
      }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const event = JSON.parse(line)
          handleEvent(event)
        } catch {
          // skip invalid JSON
        }
      }
    }
  } catch (e) {
    error.value = '请求失败: ' + (e.message || '未知错误')
  } finally {
    isStreaming.value = false
  }
}

function handleEvent(event) {
  switch (event.type) {
    case 'meta':
      metaInfo.value = { stock_code: event.stock_code, stock_name: event.stock_name }
      break
    case 'status':
      statusText.value = event.content || event.message || ''
      break
    case 'delta':
      content.value += event.content || event.text || ''
      break
    case 'thought':
      content.value += '\n> ' + (event.content || '') + '\n'
      break
    case 'done':
      statusText.value = '分析完成'
      break
    case 'error':
      error.value = event.content || event.message || '分析出错'
      break
  }
}

async function saveToHistory() {
  if (!content.value) return
  // History is auto-saved by backend
  ElMessage.success('已保存到历史记录')
}

function downloadReport() {
  if (!content.value) return
  const blob = new Blob([content.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.stockCode}_${props.historyType}_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function clearAnalysis() {
  content.value = ''
  statusText.value = ''
  error.value = ''
  metaInfo.value = null
  started.value = false
}

function showHistory() {
  historyVisible.value = true
}
</script>

<style scoped>
.ai-analysis-panel {
  min-height: 200px;
}

.start-section {
  text-align: center;
  padding: 40px 0;
}

.desc {
  color: #909399;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.6;
}
</style>
