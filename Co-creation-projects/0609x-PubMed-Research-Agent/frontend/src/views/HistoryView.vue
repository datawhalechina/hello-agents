<template>
  <div class="history-view">
    <el-card shadow="never">
      <template #header>
        <div class="history-head">
          <span class="history-title">检索历史</span>
          <el-button size="small" :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" stripe @row-click="openDetail" class="history-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="query_text" label="研究问题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="total_found" label="命中" width="80" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default>
            <el-button size="small" text type="primary">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!rows.length && !loading" description="暂无检索记录" />
    </el-card>

    <el-drawer v-model="drawerVisible" :title="detail ? detail.query_text : ''" size="70%">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detail.status)" size="small">{{ detail.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="命中数">{{ detail.total_found }}</el-descriptions-item>
          <el-descriptions-item label="检索式" :span="2">
            <code>{{ detail.pubmed_query || '-' }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="时间" :span="2">{{ formatDate(detail.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <h4>文献列表（{{ detail.articles.length }}）</h4>
        <ArticleList :articles="detail.articles" />
        <h4>AI 分析</h4>
        <SummaryReport :result="detail" />
      </template>
      <el-empty v-else description="加载中…" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getSearch, getHistory } from '@/api/search'
import { notifyError } from '@/api/http'
import ArticleList from '@/components/ArticleList.vue'
import SummaryReport from '@/components/SummaryReport.vue'
import { formatDate } from '@/utils/format'
import type { SearchListItem, SearchOut } from '@/types'

const rows = ref<SearchListItem[]>([])
const loading = ref(false)
const drawerVisible = ref(false)
const detail = ref<SearchOut | null>(null)

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await getHistory(50)
  } catch (err) {
    notifyError(err)
  } finally {
    loading.value = false
  }
}

async function openDetail(row: SearchListItem): Promise<void> {
  drawerVisible.value = true
  detail.value = null
  try {
    detail.value = await getSearch(row.id)
  } catch (err) {
    notifyError(err)
  }
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'partial') return 'warning'
  return 'info'
}

onMounted(load)
</script>

<style scoped>
.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.history-title {
  font-weight: 600;
}
.history-table {
  cursor: pointer;
}
.detail-desc {
  margin-bottom: 16px;
}
</style>
