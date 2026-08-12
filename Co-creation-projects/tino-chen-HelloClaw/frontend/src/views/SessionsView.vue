<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Card, List, Button, Empty, message } from 'ant-design-vue'
import { sessionApi, type Session } from '@/api/session'
import { useRouter } from 'vue-router'
import { PlusOutlined, DeleteOutlined, ClockCircleOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const sessions = ref<Session[]>([])
const listLoading = ref(false)
const createLoading = ref(false)

const loadSessions = async () => {
  listLoading.value = true
  try {
    const res = await sessionApi.list()
    sessions.value = res.sessions
  } catch (error) {
    message.error('加载会话列表失败')
  } finally {
    listLoading.value = false
  }
}

const createSession = async () => {
  createLoading.value = true
  try {
    const res = await sessionApi.create()
    message.success('创建会话成功')
    await loadSessions()
    router.push({ name: 'chat', query: { session: res.session_id } })
  } catch (error) {
    message.error('创建会话失败')
  } finally {
    createLoading.value = false
  }
}

const deleteSession = async (id: string) => {
  try {
    await sessionApi.delete(id)
    message.success('删除成功')
    await loadSessions()
  } catch (error) {
    message.error('删除失败')
  }
}

const formatDate = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSessions()
})
</script>

<template>
  <div class="sessions-view">
    <div class="sessions-header">
      <div>
        <h1>会话管理</h1>
        <p>查看和管理你的对话历史</p>
      </div>
      <Button type="primary" :loading="createLoading" @click="createSession">
        <PlusOutlined /> 新建会话
      </Button>
    </div>

    <div class="sessions-content">
      <Card v-if="sessions.length > 0" class="sessions-card">
        <List :data-source="sessions" :loading="listLoading">
          <template #renderItem="{ item }">
            <List.Item class="session-item">
              <List.Item.Meta>
                <template #title>
                  <span class="session-title">{{ item.id }}</span>
                </template>
                <template #description>
                  <span class="session-time">
                    <ClockCircleOutlined /> {{ formatDate(item.updated_at) }}
                  </span>
                </template>
              </List.Item.Meta>
              <template #actions>
                <button
                  class="open-btn"
                  @click="router.push({ name: 'chat', query: { session: item.id } })"
                >
                  打开
                </button>
                <button
                  class="delete-btn"
                  @click="deleteSession(item.id)"
                  title="删除"
                >
                  <DeleteOutlined />
                </button>
              </template>
            </List.Item>
          </template>
        </List>
      </Card>

      <Card v-else class="empty-card">
        <Empty description="暂无会话记录">
          <Button type="primary" @click="createSession">
            <PlusOutlined /> 创建第一个会话
          </Button>
        </Empty>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.sessions-view {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-sizing: border-box;
}

.sessions-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.sessions-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 500;
}

.sessions-header p {
  margin: 0;
  color: #999;
}

.sessions-content {
  flex: 1;
  overflow-y: auto;
}

.sessions-card {
  max-width: 800px;
}

.session-item {
  padding: 16px 0;
}

.session-title {
  font-weight: 500;
  font-family: monospace;
}

.session-time {
  color: #999;
  font-size: 13px;
}

/* 打开按钮 - 黑色字体，hover 红色 */
.open-btn {
  padding: 0 8px;
  height: 22px;
  font-size: 12px;
  line-height: 20px;
  border: none;
  background: transparent;
  color: #333;
  cursor: pointer;
  transition: color 0.2s ease;
}

.open-btn:hover {
  color: #ff4d4f;
}

/* 删除按钮 - 黑色图标 */
.delete-btn {
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: #333;
  cursor: pointer;
  transition: color 0.2s ease;
}

.delete-btn:hover {
  color: #ff4d4f;
}

.empty-card {
  max-width: 400px;
  margin: 60px auto;
}
</style>
