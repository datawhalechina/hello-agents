<script setup lang="ts">
import { ref } from 'vue'
import LatexInline from '@/components/LatexInline.vue'
import type { Paper } from '@/types'
const props = withDefaults(defineProps<{
  paper: Paper
  index?: number
  abstractPreviewChars?: number
  showTags?: boolean
  showArxivId?: boolean
  tagColor?: string
  tagLabel?: string
}>(), {
  index: 0,
  abstractPreviewChars: 320,
  showTags: true,
  showArxivId: true,
  tagColor: 'blue',
  tagLabel: '',
})
const emit = defineEmits<{
  click: [paper: Paper]
}>()
const expanded = ref(false)
function needsToggle(text?: string): boolean {
  return (text?.length ?? 0) > props.abstractPreviewChars
}
function preview(text?: string): string {
  const t = (text ?? '').trim()
  return t.length <= props.abstractPreviewChars ? t : t.slice(0, props.abstractPreviewChars) + '…'
}
function authors(paper: Paper): string {
  return (paper.authors || []).map((a) => a.name).filter(Boolean).join(', ') || '—'
}
</script>
<template>
  <a-list-item>
    <a-list-item-meta>
      <template #title>
        <div class="paper-title-block">
          <span v-if="index > 0" class="paper-index">{{ index }}.</span>
          <div class="paper-title-main">
            <div class="paper-title-row">
              <div class="paper-title-text">
                <a v-if="paper.source_url" class="paper-title-link" :href="paper.source_url" target="_blank"
                  rel="noopener noreferrer" @click="emit('click', paper)">
                  <LatexInline :text="paper.title" />
                </a>
                <LatexInline v-else class="paper-title-link" :text="paper.title" />
              </div>
              <div v-if="showTags" class="paper-title-tags">
                <a-tag v-if="tagLabel" :color="tagColor">{{ tagLabel }}</a-tag>
                <a-tag v-if="showArxivId && paper.arxiv_id" color="orange">arXiv {{ paper.arxiv_id }}</a-tag>
                <slot name="tags" />
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #description>
        <div class="paper-info">
          <p><strong>作者：</strong>{{ authors(paper) }}</p>
          <p><strong>来源：</strong><LatexInline :text="`${paper.journal || '—'} · ${paper.year ?? '—'}`" /></p>
          <div v-if="paper.abstract" class="paper-info__abstract-block">
            <p class="paper-info__abstract">
              <strong>摘要：</strong>
              <LatexInline :text="expanded ? (paper.abstract ?? '') : preview(paper.abstract)" />
            </p>
            <a-button v-if="needsToggle(paper.abstract)" type="link" size="small"
              class="paper-info__abstract-toggle" @click.stop="expanded = !expanded">
              {{ expanded ? '收起' : '展开全文' }}
            </a-button>
          </div>
          <slot name="description" />
        </div>
      </template>
    </a-list-item-meta>
    <template #actions>
      <a v-if="paper.pdf_url" :href="paper.pdf_url" target="_blank" @click="emit('click', paper)">
        <a-button type="link">PDF</a-button>
      </a>
      <slot name="actions" />
    </template>
  </a-list-item>
</template>
<style scoped>
.paper-title-block { display: flex; align-items: flex-start; gap: 6px; }
.paper-index { flex-shrink: 0; color: #999; font-weight: 600; min-width: 24px; }
.paper-title-main { flex: 1; min-width: 0; }
.paper-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.paper-title-text { flex: 1; min-width: 0; }
.paper-title-link { font-weight: 600; font-size: 15px; color: #1890ff; word-break: break-word; }
.paper-title-tags { display: flex; gap: 4px; flex-shrink: 0; flex-wrap: wrap; }
.paper-info { font-size: 13px; color: #555; }
.paper-info p { margin-bottom: 4px; }
.paper-info__abstract-block { position: relative; }
.paper-info__abstract { white-space: pre-wrap; word-break: break-word; margin-bottom: 2px; }
.paper-info__abstract-toggle { padding: 0; height: auto; font-size: 12px; }
</style>