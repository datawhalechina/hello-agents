<template>
  <div class="graph-view">
    <el-card shadow="never" class="stats-card">
      <template #header>
        <div class="head">
          <span class="page-title">知识图谱</span>
          <el-tag v-if="stats" :type="stats.ready ? 'success' : 'danger'" size="small">
            {{ stats.ready ? 'Neo4j 已连接' : 'Neo4j 未连接' }}
          </el-tag>
        </div>
      </template>

      <div class="stat-grid">
        <div class="stat-item">
          <div class="num">{{ stats ? stats.papers : '-' }}</div>
          <div class="label">文献节点</div>
        </div>
        <div class="stat-item">
          <div class="num">{{ stats ? stats.authors : '-' }}</div>
          <div class="label">作者节点</div>
        </div>
        <div class="stat-item">
          <div class="num">{{ stats ? stats.journals : '-' }}</div>
          <div class="label">期刊节点</div>
        </div>
      </div>

      <el-alert
        v-if="stats && !stats.ready"
        type="warning"
        :closable="false"
        :title="stats.error || 'Neo4j 不可用'"
        class="error-alert"
      />
      <p class="hint">
        检索结果会自动进入图谱。单击蓝色文献节点即可把它设为中心；发现有价值的论文后可直接收藏，供 AI 收藏文献问答使用。
      </p>
    </el-card>

    <el-card shadow="never" class="explore-card">
      <template #header><span class="page-title">关联文献探索</span></template>
      <div class="explore-row">
        <el-input
          v-model="pmid"
          placeholder="输入 PMID，例如 39990664"
          clearable
          size="large"
          style="max-width: 320px"
          @keyup.enter="navigateToPaper(pmid)"
        />
        <el-button type="primary" size="large" :loading="loading" @click="navigateToPaper(pmid)">
          查询关联
        </el-button>
      </div>
      <div v-if="indexedPapers.length" class="quick-start">
        <span class="quick-label">最近入图：</span>
        <el-button
          v-for="paper in indexedPapers.slice(0, 6)"
          :key="paper.pmid"
          size="small"
          plain
          @click="navigateToPaper(paper.pmid)"
        >
          {{ paper.title || `PMID ${paper.pmid}` }}
        </el-button>
      </div>
      <el-alert v-if="error" type="error" :closable="false" :title="error" class="error-alert" />

      <template v-if="subgraph && subgraph.nodes.length">
        <div class="graph-workspace">
          <GraphCanvas
            class="canvas"
            :nodes="subgraph.nodes"
            :links="subgraph.links"
            :center-id="`paper:${subgraph.pmid}`"
            :selected-id="selectedNode?.id"
            @select="handleNodeSelect"
          />

          <aside class="detail-panel">
            <template v-if="selectedNode">
              <div class="detail-head">
                <el-tag :type="nodeTagType(selectedNode.type)" size="small">
                  {{ nodeTypeLabel(selectedNode.type) }}
                </el-tag>
                <span v-if="selectedNode.pmid" class="detail-pmid">PMID {{ selectedNode.pmid }}</span>
              </div>

              <template v-if="selectedNode.type === 'paper'">
                <h3 class="detail-title">{{ selectedPaper?.title || selectedNode.label }}</h3>
                <div class="detail-meta">
                  <span v-if="selectedPaper?.journal">{{ selectedPaper.journal }}</span>
                  <span v-if="selectedPaper?.publish_date">{{ selectedPaper.publish_date }}</span>
                  <span v-if="selectedPaper?.doi">DOI {{ selectedPaper.doi }}</span>
                </div>
                <p v-if="selectedPaper?.authors.length" class="detail-authors">
                  {{ selectedPaper.authors.join(', ') }}
                </p>
                <p class="detail-abstract">
                  {{ selectedPaper?.abstract || '图谱中暂无摘要。' }}
                </p>
                <div class="detail-actions">
                  <el-link
                    type="primary"
                    :href="pubmedPaperUrl(selectedNode.pmid)"
                    target="_blank"
                    rel="noopener"
                  >打开 PubMed</el-link>
                  <el-button
                    v-if="selectedPaper"
                    size="small"
                    :type="library.isSaved(selectedPaper.pmid) ? 'warning' : 'primary'"
                    plain
                    @click="toggleFavorite"
                  >
                    {{ library.isSaved(selectedPaper.pmid) ? '取消收藏' : '收藏到 RAG' }}
                  </el-button>
                  <CopyButton :text="selectedNode.pmid" />
                </div>
              </template>

              <template v-else>
                <h3 class="detail-title">{{ selectedNode.label }}</h3>
                <p class="detail-abstract">
                  当前图中与该{{ nodeTypeLabel(selectedNode.type) }}直接相连的文献共
                  {{ connectedPaperCount }} 篇。可以前往 PubMed 查看它的完整研究脉络。
                </p>
                <el-link :href="entityPubmedUrl" target="_blank" rel="noopener" type="primary">
                  在 PubMed 检索该{{ nodeTypeLabel(selectedNode.type) }}
                </el-link>
              </template>
            </template>
            <el-empty v-else description="单击节点查看详情" :image-size="72" />
          </aside>
        </div>

        <h4 class="sub-title">关联文献列表（{{ related.length }}）</h4>
        <el-table
          v-if="related.length"
          :data="related"
          stripe
          class="related-table"
          row-class-name="clickable-row"
          @row-click="(row: RelatedPaper) => navigateToPaper(row.pmid)"
        >
          <el-table-column label="PMID" width="120">
            <template #default="{ row }">
              <el-link type="primary" @click.stop="navigateToPaper(row.pmid)">{{ row.pmid }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
          <el-table-column label="关联依据" min-width="260">
            <template #default="{ row }">
              <div class="reason-list">
                <el-tag v-for="name in row.shared_authors" :key="`a-${name}`" size="small" type="warning">
                  共同作者：{{ name }}
                </el-tag>
                <el-tag v-for="name in row.shared_journals" :key="`j-${name}`" size="small" type="success">
                  同一期刊：{{ name }}
                </el-tag>
                <span v-if="!row.shared_authors.length && !row.shared_journals.length">关系共现 {{ row.overlap }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="overlap" label="共现数" width="90" align="center" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-link type="primary" @click.stop="navigateToPaper(row.pmid)">设为中心</el-link>
              <el-link
                type="primary"
                :href="pubmedPaperUrl(row.pmid)"
                target="_blank"
                rel="noopener"
                class="pubmed-link"
                @click.stop
              >PubMed</el-link>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无关联文献（该文献尚未与其他文献共享作者或期刊）" />
      </template>
      <el-empty
        v-else-if="!loading && explored"
        description="该 PMID 暂无图谱数据（请先完成一次检索并确认 Neo4j 已连接）"
      />
      <el-empty v-else-if="!loading" description="输入 PMID 查询共享作者或期刊的关联文献" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getGraphPaper,
  getGraphPapers,
  getGraphStats,
  getRelatedPapers,
  getSubgraph
} from '@/api/graph'
import { notifyError } from '@/api/http'
import { useLibraryStore } from '@/stores/library'
import CopyButton from '@/components/CopyButton.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import type {
  Article,
  GraphNode,
  GraphPaper,
  GraphPaperSummary,
  GraphStats,
  GraphSubgraph,
  RelatedPaper
} from '@/types'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const stats = ref<GraphStats | null>(null)
const pmid = ref('')
const subgraph = ref<GraphSubgraph | null>(null)
const related = ref<RelatedPaper[]>([])
const indexedPapers = ref<GraphPaperSummary[]>([])
const selectedNode = ref<GraphNode | null>(null)
const selectedPaper = ref<GraphPaper | null>(null)
const loading = ref(false)
const explored = ref(false)
const error = ref('')
let requestToken = 0

const connectedPaperCount = computed(() => {
  if (!selectedNode.value || !subgraph.value) return 0
  const connectedIds = new Set<string>()
  for (const link of subgraph.value.links) {
    if (link.source === selectedNode.value.id) connectedIds.add(link.target)
    if (link.target === selectedNode.value.id) connectedIds.add(link.source)
  }
  return subgraph.value.nodes.filter((node) => connectedIds.has(node.id) && node.type === 'paper').length
})

const entityPubmedUrl = computed(() => {
  if (!selectedNode.value) return 'https://pubmed.ncbi.nlm.nih.gov/'
  const field = selectedNode.value.type === 'author' ? 'Author' : 'Journal'
  return `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(`${selectedNode.value.label}[${field}]`)}`
})

async function loadStats(): Promise<void> {
  try {
    const [nextStats, papers] = await Promise.all([getGraphStats(), getGraphPapers(20)])
    stats.value = nextStats
    indexedPapers.value = papers.papers
  } catch (err) {
    notifyError(err)
  }
}

async function loadGraph(id: string): Promise<void> {
  const cleanId = id.trim()
  if (!cleanId) return
  const token = ++requestToken
  pmid.value = cleanId
  loading.value = true
  explored.value = true
  error.value = ''
  try {
    const [nextGraph, nextRelated] = await Promise.all([
      getSubgraph(cleanId, 20),
      getRelatedPapers(cleanId, 20)
    ])
    if (token !== requestToken) return
    subgraph.value = nextGraph
    related.value = nextRelated.related
    selectedNode.value = nextGraph.nodes.find((node) => node.id === `paper:${cleanId}`) || null
    try {
      selectedPaper.value = await getGraphPaper(cleanId)
    } catch {
      selectedPaper.value = null
    }
  } catch (err) {
    if (token !== requestToken) return
    subgraph.value = null
    related.value = []
    selectedNode.value = null
    selectedPaper.value = null
    error.value = err instanceof Error ? err.message : '关联文献查询失败'
    notifyError(err)
  } finally {
    if (token === requestToken) loading.value = false
  }
}

async function navigateToPaper(value: string): Promise<void> {
  const id = value.trim()
  if (!id || loading.value) return
  if (String(route.query.pmid || '') === id) {
    await loadGraph(id)
    return
  }
  await router.push({ name: 'graph', query: { pmid: id } })
}

async function handleNodeSelect(node: GraphNode): Promise<void> {
  selectedNode.value = node
  if (node.type === 'paper' && node.pmid) {
    await navigateToPaper(node.pmid)
    return
  }
  selectedPaper.value = null
}

function toggleFavorite(): void {
  if (!selectedPaper.value) return
  const paper = selectedPaper.value
  const article: Article = {
    pmid: paper.pmid,
    title: paper.title,
    abstract: paper.abstract,
    doi: paper.doi,
    authors: paper.authors.map((name) => ({
      last_name: name,
      fore_name: '',
      initials: '',
      affiliation: ''
    })),
    journal: paper.journal,
    publish_date: paper.publish_date,
    publication_type: '',
    impact_factor: null
  }
  library.toggle(article)
}

function pubmedPaperUrl(id: string): string {
  return `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(id)}/`
}

function nodeTypeLabel(type: string): string {
  return { paper: '文献', author: '作者', journal: '期刊' }[type] || '节点'
}

function nodeTagType(type: string): 'primary' | 'warning' | 'success' | 'info' {
  if (type === 'paper') return 'primary'
  if (type === 'author') return 'warning'
  if (type === 'journal') return 'success'
  return 'info'
}

watch(
  () => route.query.pmid,
  (value) => {
    if (typeof value === 'string' && value.trim()) void loadGraph(value)
  },
  { immediate: true }
)

onMounted(loadStats)
</script>

<style scoped>
.stats-card {
  margin-bottom: 16px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-weight: 600;
}
.stat-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}
.stat-item {
  flex: 1;
  text-align: center;
  padding: 16px 0;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}
.num {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.label {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.hint {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.7;
}
.error-alert {
  margin-bottom: 12px;
}
.explore-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.quick-start {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: -4px 0 16px;
}
.quick-start :deep(.el-button) {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.quick-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.graph-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 16px;
  align-items: stretch;
}
.canvas {
  min-width: 0;
}
.detail-panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-bg-color);
  min-height: 480px;
  overflow: hidden;
}
.detail-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.detail-pmid {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.detail-title {
  margin: 0 0 10px;
  font-size: 16px;
  line-height: 1.55;
}
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 10px;
}
.detail-authors {
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.6;
}
.detail-abstract {
  max-height: 230px;
  overflow-y: auto;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 1.7;
}
.detail-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}
.sub-title {
  margin: 18px 0 10px;
  font-weight: 600;
}
.related-table {
  margin-top: 4px;
}
.reason-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.pubmed-link {
  margin-left: 12px;
}
:deep(.clickable-row) {
  cursor: pointer;
}
@media (max-width: 1100px) {
  .graph-workspace {
    grid-template-columns: 1fr;
  }
  .detail-panel {
    min-height: auto;
  }
}
</style>
