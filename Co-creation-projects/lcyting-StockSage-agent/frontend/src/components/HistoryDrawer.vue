<template>
  <el-drawer v-model="visible" :title="title" size="500px" @open="loadHistory">
    <div v-loading="loading">
      <div v-if="items.length === 0 && !loading" class="empty">
        暂无历史记录
      </div>

      <div v-for="item in items" :key="item.id" class="history-item">
        <div class="item-header">
          <el-tag :type="typeTag(item.type)" size="small">{{ typeLabel(item.type) }}</el-tag>
          <span class="item-title">{{ item.title || item.stock_name || item.stock_code || '--' }}</span>
          <span class="item-date">{{ item.date }}</span>
        </div>
        <div class="item-preview" v-html="previewContent(item.content)"></div>
        <div class="item-actions">
          <el-button size="small" text @click="viewDetail(item)">查看详情</el-button>
          <el-button size="small" text type="danger" @click="deleteItem(item.id)">删除</el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="detailTitle" width="700px">
      <div class="detail-content" v-html="detailContent"></div>
    </el-dialog>
  </el-drawer>
</template>

<script>
export default { name: 'HistoryDrawer' }
</script>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  type: { type: String, default: '' },
})

const emit = defineEmits(['update:visible'])

const visible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const loading = ref(false)
const items = ref([])
const detailVisible = ref(false)
const detailTitle = ref('')
const detailContent = ref('')

const title = computed(() => {
  const labels = {
    sentiment: '舆情分析历史',
    data_analysis: '数据分析历史',
    buffett: '巴菲特评估历史',
    chat: 'AI对话历史',
  }
  return labels[props.type] || '分析历史记录'
})

async function loadHistory() {
  loading.value = true
  try {
    const params = props.type ? { type: props.type } : {}
    const res = await api.get('/history/list', { params })
    if (res.code === 0 && res.data) {
      items.value = res.data.items || []
    }
  } catch (e) {
    console.error('加载历史记录失败:', e)
  } finally {
    loading.value = false
  }
}

function typeLabel(type) {
  const labels = {
    sentiment: '舆情分析',
    data_analysis: '数据分析',
    buffett: '巴菲特评估',
    chat: 'AI对话',
  }
  return labels[type] || type
}

function typeTag(type) {
  const tags = {
    sentiment: 'warning',
    data_analysis: 'primary',
    buffett: 'danger',
    chat: 'success',
  }
  return tags[type] || 'info'
}

function previewContent(content) {
  if (!content) return ''
  const text = content.substring(0, 150)
  return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

function viewDetail(item) {
  detailTitle.value = item.title || '分析详情'
  detailContent.value = (item.content || '').replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  detailVisible.value = true
}

async function deleteItem(id) {
  try {
    await ElMessageBox.confirm('确定删除这条历史记录？', '确认删除', { type: 'warning' })
    await api.delete(`/history/${id}`)
    ElMessage.success('已删除')
    loadHistory()
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.empty {
  text-align: center;
  color: #c0c4cc;
  padding: 40px 0;
  font-size: 14px;
}

.history-item {
  padding: 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.item-title {
  font-weight: 500;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-date {
  font-size: 12px;
  color: #c0c4cc;
}

.item-preview {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
}

.item-actions {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.detail-content {
  max-height: 500px;
  overflow-y: auto;
  line-height: 1.8;
  font-size: 14px;
}
</style>
