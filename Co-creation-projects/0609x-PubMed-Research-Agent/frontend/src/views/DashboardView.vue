<template>
  <div class="dashboard-view" v-loading="loading">
    <el-empty v-if="!loading && !stats" description="看板数据为空，完成检索后将在这里展示统计" />

    <template v-else-if="stats">
      <el-row :gutter="12" class="stat-row">
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="stat-card">
            <div class="num">{{ stats.total_searches }}</div>
            <div class="label">累计检索</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="stat-card">
            <div class="num">{{ stats.total_articles }}</div>
            <div class="label">累计文献</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="never" class="stat-card">
            <div class="num">{{ knownRatio }}</div>
            <div class="label">期刊影响因子收录率</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="section">
            <template #header><span class="title">📚 期刊 Top{{ stats.journals.length || 10 }}</span></template>
            <el-empty v-if="!stats.journals.length" description="暂无数据" :image-size="50" />
            <div v-else class="bars">
              <div v-for="j in stats.journals" :key="j.name" class="bar-row">
                <span class="bar-label">{{ j.name }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: journalWidth(j.count) }" />
                </div>
                <span class="bar-count">{{ j.count }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="section">
            <template #header><span class="title">📅 发文年份趋势</span></template>
            <el-empty v-if="!stats.years.length" description="暂无数据" :image-size="50" />
            <div v-else class="bars">
              <div v-for="y in stats.years" :key="y.year" class="bar-row">
                <span class="bar-label year">{{ y.year }}</span>
                <div class="bar-track">
                  <div class="bar-fill year-fill" :style="{ width: yearWidth(y.count) }" />
                </div>
                <span class="bar-count">{{ y.count }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="section">
            <template #header><span class="title">🏅 影响因子分布</span></template>
            <div v-if="stats.impact_factor_buckets.length" class="bars">
              <div v-for="b in stats.impact_factor_buckets" :key="b.bucket" class="bar-row">
                <span class="bar-label if-label">{{ b.bucket }}</span>
                <div class="bar-track">
                  <div class="bar-fill if-fill" :style="{ width: ifWidth(b.count) }" />
                </div>
                <span class="bar-count">{{ b.count }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无数据" :image-size="50" />
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="section">
            <template #header>
              <div class="kw-head">
                <span class="title">🔑 热门检索词</span>
                <div class="kw-actions">
                  <el-button
                    v-if="stats.excluded_keywords.length"
                    size="small"
                    text
                    type="primary"
                    @click="restoreAll"
                  >恢复全部</el-button>
                  <el-button
                    size="small"
                    text
                    type="danger"
                    :disabled="!stats.top_keywords.length"
                    @click="excludeAll"
                  >删除全部</el-button>
                </div>
              </div>
            </template>
            <el-empty v-if="!stats.top_keywords.length" description="暂无数据" :image-size="50" />
            <div v-else class="keywords">
              <el-tag
                v-for="k in stats.top_keywords"
                :key="k.keyword"
                size="large"
                effect="plain"
                closable
                class="kw-tag"
                @close="excludeOne(k.keyword)"
              >
                {{ k.keyword }} <span class="kw-count">×{{ k.count }}</span>
              </el-tag>
            </div>
            <template v-if="stats.excluded_keywords.length">
              <el-divider content-position="left">已删除（点击可恢复）</el-divider>
              <div class="keywords">
                <el-tag
                  v-for="kw in stats.excluded_keywords"
                  :key="kw"
                  size="small"
                  type="info"
                  class="kw-tag kw-restored"
                  @click="restoreOne(kw)"
                >
                  {{ kw }} <span class="kw-restore-text">恢复</span>
                </el-tag>
              </div>
            </template>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  excludeKeyword,
  getSearchStats,
  restoreAllKeywords,
  restoreKeyword
} from '@/api/search'
import { notifyError } from '@/api/http'
import type { DashboardStats } from '@/types'

const stats = ref<DashboardStats | null>(null)
const loading = ref(false)

const maxJournal = computed(() => Math.max(1, ...(stats.value?.journals.map((j) => j.count) ?? [1])))
const maxYear = computed(() => Math.max(1, ...(stats.value?.years.map((y) => y.count) ?? [1])))
const maxIf = computed(() =>
  Math.max(1, ...(stats.value?.impact_factor_buckets.map((b) => b.count) ?? [1]))
)

const knownRatio = computed(() => {
  if (!stats.value || !stats.value.total_articles) return '-'
  const unknown =
    stats.value.impact_factor_buckets.find((b) => b.bucket === '未知')?.count ?? 0
  const pct = Math.round(((stats.value.total_articles - unknown) / stats.value.total_articles) * 100)
  return `${pct}%`
})

function journalWidth(count: number): string {
  return `${Math.round((count / maxJournal.value) * 100)}%`
}
function yearWidth(count: number): string {
  return `${Math.round((count / maxYear.value) * 100)}%`
}
function ifWidth(count: number): string {
  return `${Math.round((count / maxIf.value) * 100)}%`
}

async function load(): Promise<void> {
  loading.value = true
  try {
    stats.value = await getSearchStats()
  } catch (err) {
    notifyError(err)
    stats.value = null
  } finally {
    loading.value = false
  }
}

async function excludeOne(keyword: string): Promise<void> {
  try {
    await excludeKeyword(keyword)
    ElMessage.success(`已删除关键词：${keyword}`)
    await load()
  } catch (err) {
    notifyError(err)
  }
}

async function excludeAll(): Promise<void> {
  try {
    for (const k of stats.value?.top_keywords ?? []) {
      await excludeKeyword(k.keyword)
    }
    ElMessage.success('已删除全部热门检索词')
    await load()
  } catch (err) {
    notifyError(err)
  }
}

async function restoreOne(keyword: string): Promise<void> {
  try {
    await restoreKeyword(keyword)
    ElMessage.success(`已恢复关键词：${keyword}`)
    await load()
  } catch (err) {
    notifyError(err)
  }
}

async function restoreAll(): Promise<void> {
  try {
    await restoreAllKeywords()
    ElMessage.success('已恢复全部关键词')
    await load()
  } catch (err) {
    notifyError(err)
  }
}

onMounted(load)
</script>

<style scoped>
.stat-row {
  margin-bottom: 12px;
}
.stat-card {
  text-align: center;
  margin-bottom: 12px;
}
.num {
  font-size: 26px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.label {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.section {
  margin-bottom: 12px;
}
.title {
  font-weight: 600;
}
.kw-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar-label {
  width: 160px;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
.bar-label.year {
  width: 60px;
}
.bar-label.if-label {
  width: 50px;
}
.bar-track {
  flex: 1;
  height: 16px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--el-color-primary);
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.4s ease;
}
.year-fill {
  background: var(--el-color-warning);
}
.if-fill {
  background: var(--el-color-success);
}
.bar-count {
  width: 36px;
  text-align: right;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.kw-tag {
  font-size: 14px;
  cursor: pointer;
}
.kw-count {
  margin-left: 4px;
  color: var(--el-color-primary);
  font-weight: 600;
}
.kw-restored {
  cursor: pointer;
}
.kw-restore-text {
  margin-left: 4px;
  color: var(--el-color-primary);
}
</style>
