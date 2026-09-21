<template>
  <div class="library-view">
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span class="page-title">文献收藏（{{ store.count }}）</span>
          <div class="actions">
            <el-button size="small" :disabled="!store.count" @click="exportBibtex">导出 BibTeX</el-button>
            <el-button size="small" :disabled="!store.count" @click="exportCsv">导出 CSV</el-button>
            <el-button size="small" type="danger" plain :disabled="!store.count" @click="clearAll">清空</el-button>
          </div>
        </div>
      </template>

      <el-empty
        v-if="!store.saved.length"
        description="暂无收藏文献，在检索结果卡片中点击星标即可收藏"
      />

      <div v-else class="saved-list">
        <div v-for="art in store.saved" :key="art.pmid" class="saved-item">
          <div class="item-head">
            <el-icon class="star-icon"><StarFilled /></el-icon>
            <span class="title-text">{{ art.title || 'Untitled' }}</span>
            <el-button size="small" text type="danger" @click="store.remove(art.pmid)">移除</el-button>
          </div>
          <div class="meta-row">
            <el-tag size="small" type="info">PMID {{ art.pmid }}</el-tag>
            <el-tag v-if="art.journal" size="small" type="info">{{ art.journal }}</el-tag>
            <el-tag v-if="art.publish_date" size="small" type="warning">{{ art.publish_date }}</el-tag>
            <el-tag v-if="art.doi" size="small" type="success">{{ art.doi }}</el-tag>
            <el-tag v-if="art.impact_factor" size="small" type="danger">IF {{ art.impact_factor }}</el-tag>
          </div>

          <template v-if="translated[art.pmid] && translated[art.pmid].title">
            <p class="label">中文标题</p>
            <p class="title-zh">{{ translated[art.pmid].title }}</p>
            <p class="label">中文摘要</p>
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
              :loading="!!translated[art.pmid] && translated[art.pmid].loading"
              @click="toggleTranslate(art)"
            >
              {{ translated[art.pmid] && translated[art.pmid].title ? '显示原文' : '翻译为中文' }}
            </el-button>
            <CopyButton :text="citationText(art)" />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { ElMessageBox } from 'element-plus/es/components/message-box/index'
import CopyButton from '@/components/CopyButton.vue'
import { translateText } from '@/api/translate'
import { notifyError } from '@/api/http'
import { useLibraryStore } from '@/stores/library'
import type { SavedArticle } from '@/types'

const store = useLibraryStore()

interface LibTranslation {
  title: string
  abstract: string
  loading: boolean
}

const translated = reactive<Record<string, LibTranslation>>({})

async function toggleTranslate(art: SavedArticle): Promise<void> {
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

function citationText(art: SavedArticle): string {
  const authors = art.authors
    .map((a) => `${a.last_name} ${a.fore_name || a.initials}`.trim())
    .filter(Boolean)
    .join(', ')
  const doi = art.doi ? `\nDOI: ${art.doi}` : ''
  return `${art.title || ''}\n${authors}\n${art.journal || ''} ${art.publish_date || ''}\nPMID: ${art.pmid}${doi}`
}

function escapeBibtex(value: string): string {
  return value.replace(/([&%$#_{}~^\\])/g, '\\\\$1')
}

function bibtexAuthor(art: SavedArticle): string {
  const names = art.authors.map((a) => a.last_name || a.fore_name || '').filter(Boolean)
  return names.length ? names.join(' and ') : 'Unknown'
}

function exportBibtex(): void {
  const entries = store.saved.map((art) => {
    const year = (art.publish_date.match(/\b(19|20)\d{2}\b/) || [''])[0]
    return [
      '@article{pmid' + art.pmid + ',',
      '  title = {' + escapeBibtex(art.title || '') + '},',
      '  author = {' + escapeBibtex(bibtexAuthor(art)) + '},',
      '  journal = {' + escapeBibtex(art.journal || '') + '},',
      '  year = {' + year + '},',
      '  pmid = {' + art.pmid + '},',
      art.doi ? '  doi = {' + art.doi + '}' : '',
      '}'
    ]
      .filter((line) => line !== '')
      .join('\n')
  })
  download('pubmed-library.bib', entries.join('\n\n'))
  ElMessage.success('已导出 BibTeX')
}

function exportCsv(): void {
  const header = 'pmid,title,journal,publish_date,doi'
  const rows = store.saved.map((art) =>
    [art.pmid, art.title, art.journal, art.publish_date, art.doi]
      .map((v) => '"' + String(v || '').replace(/"/g, '""') + '"')
      .join(',')
  )
  download('pubmed-library.csv', [header, ...rows].join('\n'), 'text/csv;charset=utf-8')
  ElMessage.success('已导出 CSV')
}

function download(filename: string, content: string, mime = 'text/plain;charset=utf-8'): void {
  const blob = new Blob(['\ufeff', content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function clearAll(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定清空全部收藏文献吗？', '提示', { type: 'warning' })
    store.clear()
    ElMessage.success('已清空')
  } catch {
    /* cancelled */
  }
}
</script>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 8px;
}
.saved-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.saved-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px 16px;
}
.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.star-icon {
  color: var(--el-color-warning);
  flex-shrink: 0;
}
.title-text {
  flex: 1;
  font-weight: 600;
  line-height: 1.5;
}
.meta-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.label {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.title-zh {
  margin: 0 0 8px;
  font-weight: 600;
  line-height: 1.7;
}
.abstract {
  margin: 0 0 12px;
  line-height: 1.7;
  font-size: 14px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
</style>
