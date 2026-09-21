<template>
  <div v-if="!articles.length" class="empty-hint">暂无文献</div>
  <el-collapse v-else accordion>
    <el-collapse-item v-for="art in articles" :key="art.pmid" :name="art.pmid">
      <template #title>
        <div class="article-title">
          <span class="pmid">PMID {{ art.pmid }}</span>
          <span class="title-text">{{ art.title || 'Untitled' }}</span>
        </div>
      </template>

      <div class="article-body">
        <div class="meta-row">
          <el-tag v-if="art.journal" size="small" type="info">{{ art.journal }}</el-tag>
          <el-tag v-if="art.publish_date" size="small" type="warning">{{ art.publish_date }}</el-tag>
          <el-tag v-if="art.doi" size="small" type="success">{{ art.doi }}</el-tag>
        </div>
        <div v-if="art.authors && art.authors.length" class="authors">
          {{ formatAuthors(art.authors) }}
        </div>
        <template v-if="translated[art.pmid] && translated[art.pmid].title">
          <p class="translated-label">中文标题</p>
          <p class="translated-title">{{ translated[art.pmid].title }}</p>
          <p class="translated-label">中文摘要</p>
          <p class="abstract">{{ translated[art.pmid].abstract || '（无摘要）' }}</p>
        </template>
        <p v-else class="abstract">{{ art.abstract || 'No abstract available.' }}</p>
        <div class="actions">
          <el-link
            type="primary"
            :href="`https://pubmed.ncbi.nlm.nih.gov/${art.pmid}/`"
            target="_blank"
            rel="noopener"
          >
            <el-icon style="margin-right: 4px"><Link /></el-icon>查看 PubMed
          </el-link>
          <el-button
            size="small"
            type="primary"
            plain
            :loading="translated[art.pmid] && translated[art.pmid].loading"
            @click="toggleTranslate(art)"
          >
            {{ translated[art.pmid] && translated[art.pmid].title ? '显示原文' : '翻译为中文' }}
          </el-button>
          <el-button
            size="small"
            :type="library.isSaved(art.pmid) ? 'warning' : 'info'"
            plain
            @click="library.toggle(art)"
          >
            <el-icon style="margin-right: 4px">
              <StarFilled v-if="library.isSaved(art.pmid)" />
              <Star v-else />
            </el-icon>
            {{ library.isSaved(art.pmid) ? '已收藏' : '收藏' }}
          </el-button>
          <CopyButton :text="`${art.title}\n\n${art.abstract}\n\nPMID: ${art.pmid}`" />
        </div>
      </div>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import CopyButton from './CopyButton.vue'
import { translateText } from '@/api/translate'
import { notifyError } from '@/api/http'
import { useLibraryStore } from '@/stores/library'
import type { Article, Author } from '@/types'

defineProps<{ articles: Article[] }>()

const library = useLibraryStore()

interface ArticleTranslation {
  title: string
  abstract: string
  loading: boolean
}

const translated = reactive<Record<string, ArticleTranslation>>({})

async function toggleTranslate(art: Article): Promise<void> {
  const cur = translated[art.pmid]
  if (cur && cur.title) {
    delete translated[art.pmid]
    return
  }
  if (cur && cur.loading) return

  translated[art.pmid] = { title: '', abstract: '', loading: true }
  try {
    const titleRes = await translateText({ text: art.title, target_language: 'zh' })
    const absRes = await translateText({ text: art.abstract, target_language: 'zh' })
    translated[art.pmid] = {
      title: titleRes.translated_text,
      abstract: absRes.translated_text,
      loading: false
    }
  } catch (err) {
    delete translated[art.pmid]
    notifyError(err)
  }
}

function formatAuthors(authors: Author[]): string {
  return authors
    .map((a) => `${a.last_name} ${a.fore_name || a.initials}`.trim())
    .filter(Boolean)
    .join(', ')
}
</script>

<style scoped>
.empty-hint {
  color: var(--el-text-color-secondary);
  padding: 24px 0;
  text-align: center;
}
.article-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.pmid {
  color: var(--el-color-primary);
  font-size: 12px;
  flex-shrink: 0;
}
.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.article-body {
  padding: 4px 8px 8px;
}
.meta-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.authors {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 8px;
}
.abstract {
  margin: 0 0 12px;
  line-height: 1.7;
  font-size: 14px;
}
.translated-label {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.translated-title {
  margin: 0 0 12px;
  line-height: 1.7;
  font-size: 14px;
  font-weight: 600;
}
.actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
</style>
