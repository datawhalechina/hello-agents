<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { formatTime } from '../markdown'

const router = useRouter()
const sessions = ref([])

async function load() {
  const data = await api('/session/list')
  sessions.value = data.sessions || []
}

async function create() {
  const created = await api('/session/create', { method: 'POST', body: '{}' })
  router.push({ name: 'chat', query: { session: created.session_id } })
}

async function remove(id) {
  await api(`/session/${id}`, { method: 'DELETE' })
  if (localStorage.getItem('caa.lastSessionId') === id) {
    localStorage.removeItem('caa.lastSessionId')
  }
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head chat-head">
      <div>
        <h2>会话管理</h2>
        <p>多会话历史保存在工作空间 sessions/ 目录</p>
      </div>
      <button class="primary" @click="create">新建会话</button>
    </header>
    <div class="panel">
      <div v-if="!sessions.length" class="empty">还没有会话</div>
      <div v-for="item in sessions" :key="item.id" class="list-item">
        <div>
          <strong>{{ item.title || item.id }}</strong>
          <div class="muted">{{ formatTime(item.updated_at) }} · {{ item.id }}</div>
        </div>
        <div>
          <button class="ghost" @click="router.push({ name: 'chat', query: { session: item.id } })">打开</button>
          <button class="danger" @click="remove(item.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.chat-head .primary {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
