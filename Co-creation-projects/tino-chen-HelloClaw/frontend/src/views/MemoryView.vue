<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Card, List, Empty, message, Tag } from 'ant-design-vue'
import { memoryApi, type MemoryEntry } from '@/api/memory'
import { FileTextOutlined, CalendarOutlined } from '@ant-design/icons-vue'

const memories = ref<MemoryEntry[]>([])
const selectedMemory = ref<MemoryEntry | null>(null)
const loading = ref(false)

const loadMemories = async () => {
  loading.value = true
  try {
    const res = await memoryApi.list()
    memories.value = res.memories
  } catch (error) {
    message.error('加载记忆列表失败')
  } finally {
    loading.value = false
  }
}

const selectMemory = (memory: MemoryEntry) => {
  selectedMemory.value = memory
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (dateStr === today.toISOString().split('T')[0]) {
    return '今天'
  } else if (dateStr === yesterday.toISOString().split('T')[0]) {
    return '昨天'
  }
  return dateStr
}

const isToday = (dateStr: string) => {
  return dateStr === new Date().toISOString().split('T')[0]
}

// 简单的 markdown 格式化函数
const formatMarkdown = (content: string): string => {
  return content
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  loadMemories()
})
</script>

<template>
  <div class="memory-view">
    <div class="memory-header">
      <h1>工作记忆</h1>
      <p>查看每日工作记录的记忆</p>
    </div>

    <div class="memory-content">
      <!-- 记忆列表 -->
      <div class="memory-list">
        <Card :loading="loading" class="list-card">
          <template #title>
            <FileTextOutlined /> 每日记录
          </template>
          <List :data-source="memories" :locale="{ emptyText: '暂无工作记忆' }">
            <template #renderItem="{ item }">
              <List.Item
                @click="selectMemory(item)"
                :class="['memory-item', { active: selectedMemory?.filename === item.filename }]"
              >
                <div class="memory-item-content">
                  <div class="memory-date">
                    <CalendarOutlined />
                    <span>{{ formatDate(item.date) }}</span>
                    <Tag v-if="isToday(item.date)" color="error" size="small">今天</Tag>
                  </div>
                  <div class="memory-preview">{{ item.preview }}</div>
                </div>
              </List.Item>
            </template>
          </List>
        </Card>
      </div>

      <!-- 记忆详情 -->
      <div class="memory-detail">
        <Card v-if="selectedMemory" class="detail-card">
          <template #title>
            <span>{{ selectedMemory.date }}</span>
            <Tag v-if="isToday(selectedMemory.date)" color="error" style="margin-left: 8px">今天</Tag>
          </template>
          <div class="memory-content-text" v-html="formatMarkdown(selectedMemory.content)"></div>
        </Card>

        <Card v-else class="empty-card">
          <Empty
            description="请从左侧选择一条记忆"
            :image-style="{ height: '80px' }"
          />
        </Card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.memory-view {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-sizing: border-box;
}

.memory-header {
  flex-shrink: 0;
  margin-bottom: 24px;
}

.memory-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 500;
}

.memory-header p {
  margin: 0;
  color: #999;
}

.memory-content {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.memory-list {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-card :deep(.ant-card-body) {
  flex: 1;
  padding: 0;
  overflow-y: auto;
}

.memory-item {
  cursor: pointer;
  padding: 12px 16px;
  transition: all 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.memory-item:hover {
  background-color: #f5f5f5;
}

.memory-item.active {
  background-color: #fff1f0;
  border-left: 3px solid #ff4d4f;
}

.memory-item-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.memory-date {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #333;
}

.memory-date :deep(.anticon) {
  color: #ff5c5c;
}

.memory-preview {
  font-size: 13px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memory-detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.detail-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-card :deep(.ant-card-head) {
  flex-shrink: 0;
}

.detail-card :deep(.ant-card-body) {
  flex: 1;
  overflow-y: auto;
}

.memory-content-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.memory-content-text :deep(h2) {
  font-size: 18px;
  margin: 16px 0 12px;
  color: #333;
}

.memory-content-text :deep(h3) {
  font-size: 15px;
  margin: 12px 0 8px;
  color: #ff5c5c;
}

.empty-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
