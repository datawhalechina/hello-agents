<template>
  <div class="history-container">
    <div class="page-header">
      <h2>📋 我的历史行程</h2>
      <a-button @click="goBack">← 返回首页</a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && records.length === 0" description="暂无历史记录">
        <template #image>
          <div style="font-size: 80px;">🗺️</div>
        </template>
        <a-button type="primary" @click="goBack">去创建行程</a-button>
      </a-empty>

      <a-list v-else :data-source="records" :grid="{ gutter: 16, column: 2 }">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-card class="history-card" hoverable @click="viewDetail(item)">
              <div class="history-header">
                <span class="history-city">{{ item.city }}</span>
                <a-tag color="blue">{{ item.travel_days }}天</a-tag>
              </div>
              <div class="history-meta">
                <div>📅 {{ item.start_date }} ~ {{ item.end_date }}</div>
                <div v-if="item.traveler_group">👥 {{ item.traveler_group }}</div>
                <div class="history-time">🕐 {{ item.created_at }}</div>
              </div>
              <div class="history-prefs" v-if="item.preferences">
                <a-tag v-for="p in item.preferences.split(',')" :key="p" color="purple">{{ p }}</a-tag>
              </div>
              <template #actions>
                <a-button type="link" danger @click.stop="deleteRecord(item)">删除</a-button>
              </template>
            </a-card>
          </a-list-item>
        </template>
      </a-list>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'

const router = useRouter()
const loading = ref(false)
const records = ref<any[]>([])

/** Cookie 自动携带 token，无需手动传 header */
async function api(path: string, options: RequestInit = {}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://localhost:8000'
  return fetch(`${baseUrl}${path}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
}

async function fetchHistory() {
  loading.value = true
  try {
    const res = await api('/api/history')
    const data = await res.json()
    if (res.ok) {
      records.value = data.records || []
    } else {
      if (res.status === 401) {
        // Cookie 过期
        localStorage.removeItem('auth_username')
        router.push('/login')
        return
      }
      message.error(data.detail || '获取历史记录失败')
    }
  } catch (e) {
    message.error('网络错误')
  } finally {
    loading.value = false
  }
}

async function viewDetail(item: any) {
  try {
    const res = await api(`/api/history/${item.id}`)
    const data = await res.json()
    if (res.ok && data.record) {
      sessionStorage.setItem('tripPlan', JSON.stringify(data.record.plan_data))
      sessionStorage.setItem('travelerGroup', data.record.traveler_group || '')
      router.push('/result')
    } else {
      message.error('获取行程详情失败')
    }
  } catch (e) {
    message.error('网络错误')
  }
}

function deleteRecord(item: any) {
  Modal.confirm({
    title: `删除${item.city}行程？`,
    content: '删除后不可恢复',
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        const res = await api(`/api/history/${item.id}`, { method: 'DELETE' })
        if (res.ok) {
          message.success('已删除')
          records.value = records.value.filter((r: any) => r.id !== item.id)
        } else {
          message.error('删除失败')
        }
      } catch (e) {
        message.error('网络错误')
      }
    }
  })
}

function goBack() {
  router.push('/')
}

onMounted(fetchHistory)
</script>

<style scoped>
.history-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.history-card {
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.history-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.history-city {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}
.history-meta {
  color: #666;
  font-size: 14px;
  line-height: 2;
}
.history-time {
  color: #999;
  font-size: 12px;
}
.history-prefs {
  margin-top: 8px;
}
</style>
