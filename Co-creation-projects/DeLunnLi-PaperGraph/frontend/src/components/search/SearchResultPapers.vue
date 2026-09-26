<script setup lang="ts">
import { FilePdfOutlined, SaveOutlined } from '@ant-design/icons-vue'
import LatexInline from '@/components/LatexInline.vue'
import type { Paper } from '@/types'
import { clipTextAvoidBreakingMath } from '@/utils/markdown'
import { resultSourceMeta } from '@/utils/paperSourceMeta'

const props = defineProps<{
  papers: Paper[]
  total: number
}>()

const emit = defineEmits<{
  saveOne: [paper: Paper]
  saveAll: []
}>()

function abstractPreview(abs: string, length = 280): string {
  return clipTextAvoidBreakingMath(abs, length)
}
</script>

<template>
  <div v-if="papers.length > 0" class="papers-list">
    <div class="papers-header">
      <span>为你找到 {{ total }} 篇相关论文：</span>
      <a-button type="link" size="small" @click="emit('saveAll')">
        <SaveOutlined /> 保存全部
      </a-button>
    </div>
    <div v-for="(paper, pIndex) in papers" :key="pIndex" class="paper-item">
      <div class="paper-number">{{ pIndex + 1 }}.</div>
      <div class="paper-content">
        <div class="paper-title-line">
          <a v-if="paper.source_url" :href="paper.source_url" target="_blank" class="paper-title-link">
            <LatexInline :text="paper.title" />
          </a>
          <span v-else class="paper-title-text">
            <LatexInline :text="paper.title" />
          </span>
          <span class="paper-badges">
            <a-tag :color="resultSourceMeta(paper.source).color" size="small">
              {{ resultSourceMeta(paper.source).label }}
            </a-tag>
          </span>
        </div>
        <div class="paper-meta">
          <span v-if="paper.authors?.length">
            <strong>作者：</strong>{{ paper.authors.map(a => a.name).slice(0, 5).join(', ') }}
            <span v-if="paper.authors.length > 5"> 等</span>
          </span>
        </div>
        <div class="paper-source">
          <strong>期刊/会议：</strong>
          <LatexInline
            :text="`${paper.journal || paper.venue || (paper.source ? resultSourceMeta(paper.source).label + ' 预印本' : '—')} · ${paper.year ?? '—'}`"
          />
        </div>
        <div v-if="paper.abstract" class="paper-abstract">
          <strong>摘要：</strong>
          <LatexInline :text="abstractPreview(paper.abstract, 280)" />
        </div>
        <div class="paper-footer">
          <span class="paper-tags">
            <a-tag v-if="paper.arxiv_id" color="orange" size="small">arXiv {{ paper.arxiv_id }}</a-tag>
            <a-tag v-if="paper.citations" color="cyan" size="small">{{ paper.citations }} 引用</a-tag>
          </span>
          <span class="paper-actions">
            <a v-if="paper.pdf_url" :href="paper.pdf_url" target="_blank">
              <a-button type="link" size="small">
                <FilePdfOutlined /> PDF
              </a-button>
            </a>
            <a v-else-if="paper.doi" :href="'https://doi.org/' + paper.doi" target="_blank">
              <a-button type="link" size="small">DOI</a-button>
            </a>
            <a-button type="link" size="small" @click="emit('saveOne', paper)">
              <SaveOutlined /> 保存
            </a-button>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.papers-list {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #e2e8f0;
  margin-top: 12px;
}
.papers-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
  color: #64748b;
  margin-bottom: 16px;
  padding-bottom: 12px;
}
.paper-item {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #e2e8f0;
}
.paper-item:last-child {
  border-bottom: none;
}
.paper-number {
  font-weight: 700;
  color: #3b82f6;
  font-size: 15px;
  flex-shrink: 0;
  min-width: 24px;
}
.paper-content {
  flex: 1;
  min-width: 0;
}
.paper-title-line {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.paper-title-link {
  font-weight: 600;
  font-size: 15px;
  color: #1e40af;
}
.paper-title-text {
  font-weight: 600;
  font-size: 15px;
  color: #1e293b;
}
.paper-meta,
.paper-source,
.paper-abstract {
  font-size: 13px;
  color: #475569;
  margin-bottom: 6px;
  line-height: 1.55;
}
.paper-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.paper-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.paper-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}
.paper-title-link:hover {
  text-decoration: underline;
}
@media (max-width: 768px) {
  .paper-title-line {
    flex-direction: column;
    gap: 8px;
  }
  .paper-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
