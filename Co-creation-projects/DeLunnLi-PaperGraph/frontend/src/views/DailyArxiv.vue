<template>
  <div class="daily-page">
    <div
      v-if="loading"
      class="daily-page__loading"
      role="status"
      aria-live="polite"
      aria-label="正在加载每日推荐"
    >
      <a-spin size="large" :spinning="true" />
      <span class="daily-page__loading-text">加载论文中…</span>
    </div>
    <template v-else>
      <div v-if="!loading" class="daily-toolbar">
        <div class="daily-toolbar__row">
          <div class="daily-toolbar__left">
            <p class="daily-toolbar__headline">
              <template v-if="metaDateKey">
                <a-tag color="default" size="small" class="daily-toolbar__head-date-tag">{{ metaDateKey }}</a-tag>
              </template>
              <span class="daily-toolbar__head-core">
                <span class="daily-toolbar__head-kw">推荐构成：</span>
                <span v-if="dailySourceSummaryLine" class="daily-toolbar__head-stats">{{ dailySourceSummaryLine }}</span>
              </span>
            </p>
            <p v-if="dailyStrategyDetailBody" class="daily-toolbar__head-strategy-more">{{ dailyStrategyDetailBody }}</p>
          </div>
          <div class="daily-toolbar__actions">
            <a-button type="primary" :loading="refreshing" @click="reloadDaily(true)">{{ refreshButtonText }}</a-button>
          </div>
        </div>
        <div
          v-if="preferenceTitleCoKeywords.length > 0 || randomTitleCoKeywords.length > 0"
          class="daily-toolbar__section daily-toolbar__section--split-kw"
        >
          <div v-if="preferenceTitleCoKeywords.length > 0" class="daily-toolbar__kw-panel">
            <span class="daily-toolbar__kw-title">个性化推荐：</span>
            <div class="daily-toolbar__tag-row daily-toolbar__tag-row--kw">
              <a-tag v-for="kw in preferenceTitleCoKeywords" :key="`pref-${kw}`" color="purple">{{ kw }}</a-tag>
            </div>
          </div>
          <div v-if="randomTitleCoKeywords.length > 0" class="daily-toolbar__kw-panel">
            <span class="daily-toolbar__kw-title">随机推荐：</span>
            <div class="daily-toolbar__tag-row daily-toolbar__tag-row--kw">
              <a-tag v-for="kw in randomTitleCoKeywords" :key="`rnd-${kw}`" color="processing">{{ kw }}</a-tag>
            </div>
          </div>
        </div>
        <div v-if="listTopCategories.length > 0" class="daily-toolbar__section">
          <div class="daily-toolbar__section-head">本页领域</div>
          <div class="daily-toolbar__tag-row">
            <a-tag v-for="(c, i) in listTopCategories" :key="`cat-${i}-${c}`" color="cyan">{{ c }}</a-tag>
          </div>
        </div>
      </div>
      <a-alert
        v-if="emptyHint"
        type="info"
        show-icon
        class="daily-page__alert"
        :message="emptyHint"
      >
        <template #action>
          <a-button size="small" type="primary" :loading="refreshing" @click="reloadDaily(true)">重新拉取</a-button>
        </template>
      </a-alert>
      <a-card v-if="searchResults.length > 0" :bordered="false" class="daily-results-card" title="推荐列表">
        <template #extra>
          <span class="daily-results-card__hint">含个性化与当日精选，可保存到文献库</span>
        </template>
      <a-list
        class="daily-paper-list"
        :data-source="searchResults"
        :pagination="{
          pageSize: 10,
          total: searchResults.length,
          showTotal: (t: number) => `共 ${t} 篇`,
        }"
      >
        <template #renderItem="{ item, index }">
          <PaperCard :paper="item" :index="index + 1" :tag-color="randomIds.has(item.arxiv_id || '') ? 'gold' : 'blue'"
            :tag-label="randomIds.has(item.arxiv_id || '') ? '随机' : '个性化'" @click="onPaperClick">
            <template #actions>
              <a-button type="link" @click="saveOne(item)">保存</a-button>
              <a-button v-if="hintFor(item)" type="link" @click="showWhyAndMaybeRead(item)">为什么</a-button>
              <a-tooltip title="不感兴趣，后续减少类似推荐">
                <a-button type="link" danger @click="skipOne(item, index)"><CloseOutlined /> 不感兴趣</a-button>
              </a-tooltip>
            </template>
          </PaperCard>
        </template>
      </a-list>
    </a-card>
    <a-empty v-else-if="!emptyHint" class="daily-page__empty" description="暂无推荐论文" />
    </template>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { CloseOutlined } from '@ant-design/icons-vue'
import PaperCard from '@/components/shared/PaperCard.vue'
import { savePapers, getDailyPapers, postDailyRecommendFeedback, type DailyPapersApiResponse } from '@/services/api'
import type { Paper } from '@/types'
import { titleCoKeywordsFromPapers } from '@/composables/useTitleKeywords'
const searchResults = ref<Paper[]>([])
const randomIds = ref<Set<string>>(new Set())
const loading = ref(true)
const refreshing = ref(false)
const emptyHint = ref<string | null>(null)
const metaDateKey = ref('')
const dailyPersonalizedTotal = ref<number | null>(null)
const dailyArxivSelectedTotal = ref<number | null>(null)
const dailyStrategyExplanation = ref('')
const skippedIds = ref<Set<string>>(new Set())
const hintsMap = ref<Map<string, { kind: string; explanation: string }>>(new Map())
const personalizedThemeKeywordsLlm = ref<string[]>([])
const generalThemeKeywordsLlm = ref<string[]>([])
const router = useRouter()
function normThemeKeywordList(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((s) => s.trim())
}
function topCategoriesFromPapers(papers: Paper[], limit = 4): string[] {
  const freq = new Map<string, number>()
  for (const p of papers) {
    const c = (p.category || '').trim()
    if (!c) continue
    freq.set(c, (freq.get(c) ?? 0) + 1)
  }
  return [...freq.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([k]) => k)
}
const preferenceTitleCoKeywords = computed(() => {
  if (personalizedThemeKeywordsLlm.value.length > 0) {
    return personalizedThemeKeywordsLlm.value.slice(0, 8)
  }
  const rid = randomIds.value
  const personalized = searchResults.value.filter((p) => !rid.has(p.arxiv_id || ''))
  return titleCoKeywordsFromPapers(personalized, 5)
})
const randomTitleCoKeywords = computed(() => {
  if (generalThemeKeywordsLlm.value.length > 0) {
    return generalThemeKeywordsLlm.value.slice(0, 8)
  }
  const rid = randomIds.value
  const general = searchResults.value.filter((p) => rid.has(p.arxiv_id || ''))
  return titleCoKeywordsFromPapers(general, 5)
})
const listTopCategories = computed(() => topCategoriesFromPapers(searchResults.value, 4))
const dailySourceSummaryLine = computed(() => {
  const bits: string[] = []
  if (dailyPersonalizedTotal.value != null) {
    bits.push(`个性化 ${dailyPersonalizedTotal.value} 篇`)
  }
  if (dailyArxivSelectedTotal.value != null) {
    bits.push(`当日精选 ${dailyArxivSelectedTotal.value} 篇`)
  }
  return bits.join(' · ')
})
const STRATEGY_MAX_CHARS = 360
const STRATEGY_MAX_LINES = 4
function strategyExplanationLooksRenderable(raw: string): boolean {
  const s = raw.trim()
  if (!s) return false
  if (s.length > STRATEGY_MAX_CHARS) return false
  const lines = s.split(/\r?\n/).filter((l) => l.trim().length > 0)
  if (lines.length > STRATEGY_MAX_LINES) return false
  if (
    /阅读记忆关键词|数据源条数|arXiv OR 查询[:：]|个性化推荐：多样|通用推荐：多样|候选池规模[:：]/.test(s)
  ) {
    return false
  }
  if ((s.match(/[、，,]/g) || []).length > 18) return false
  return true
}
const dailyStrategyDetailBody = computed(() => {
  const raw = dailyStrategyExplanation.value.trim()
  if (!raw || !strategyExplanationLooksRenderable(raw)) return ''
  return raw
})
const refreshButtonText = computed(() => refreshing.value ? '刷新中…' : '刷新论文')
function dailyPaperIdentity(paper: Paper): string {
  if (paper.arxiv_id) return `arxiv:${paper.arxiv_id}`
  if (paper.doi) return `doi:${paper.doi}`
  return `title:${paper.title || ''}:${paper.year || ''}`
}
function dailyListSignature(papers: Paper[]): string {
  return papers.map(dailyPaperIdentity).join('|')
}
function applyDailyPayload(r: DailyPapersApiResponse) {
  metaDateKey.value = (r.date_key && String(r.date_key).trim()) || ''
  dailyPersonalizedTotal.value = typeof r.personalized_total === 'number' ? r.personalized_total : null
  dailyArxivSelectedTotal.value = typeof r.arxiv_selected_total === 'number' ? r.arxiv_selected_total : null
  dailyStrategyExplanation.value = (r.strategy_explanation && String(r.strategy_explanation).trim()) || ''
  personalizedThemeKeywordsLlm.value = normThemeKeywordList(r.personalized_theme_keywords)
  generalThemeKeywordsLlm.value = normThemeKeywordList(r.general_theme_keywords)
  const rr = [...(r.arxiv_selected || [])]
  const pr = [...(r.personalized || [])]
  randomIds.value = new Set(rr.map((p) => p.arxiv_id || '').filter(Boolean))
  const hints = new Map<string, { kind: string; explanation: string }>()
  r.personalized_pick_hints?.forEach((h) => {
    hints.set(h.identity_key, { kind: h.pick_kind, explanation: h.explanation })
  })
  r.general_pick_hints?.forEach((h) => {
    hints.set(h.identity_key, { kind: h.pick_kind, explanation: h.explanation })
  })
  hintsMap.value = hints
  const maxLen = Math.max(rr.length, pr.length)
  const interleaved: typeof pr = []
  for (let i = 0; i < maxLen; i++) {
    if (i < rr.length) interleaved.push(rr[i])
    if (i < pr.length) interleaved.push(pr[i])
  }
  const filtered = interleaved.filter((p) => {
    const identity = p.arxiv_id ? `arxiv:${p.arxiv_id}` : p.doi ? `doi:${p.doi}` : `title_hash:${p.title}_${p.year}`
    return !skippedIds.value.has(identity)
  })
  searchResults.value = filtered
  if (!filtered.length) {
    emptyHint.value = (r.message && r.message.trim()) || '今日未从数据源取到足够候选（可稍后点「重新拉取」）。'
  } else {
    emptyHint.value = null
  }
}
function dailyPayloadHasPapers(r: DailyPapersApiResponse): boolean {
  return (r.arxiv_selected?.length ?? 0) + (r.personalized?.length ?? 0) > 0
}
async function reloadDaily(forceRefresh: boolean) {
  if (forceRefresh) refreshing.value = true
  else if (searchResults.value.length === 0) loading.value = true
  emptyHint.value = null
  const previousSkipped = new Set(skippedIds.value)
  const previousSignature = dailyListSignature(searchResults.value)
  if (forceRefresh) skippedIds.value = new Set()
  try {
    const r = await getDailyPapers(forceRefresh ? { force_refresh: true } : {})
    if (!r?.success) throw new Error(r?.message || '加载失败')
    if (forceRefresh && !dailyPayloadHasPapers(r) && searchResults.value.length > 0) {
      skippedIds.value = previousSkipped
      emptyHint.value = r.message || '刷新未取到新结果，已保留当前列表。'
      message.warning(emptyHint.value)
      return
    }
    applyDailyPayload(r)
    if (forceRefresh) {
      const currentSignature = dailyListSignature(searchResults.value)
      if (r.refresh_failed) {
        message.warning(r.message || '刷新失败，已显示上次缓存结果。')
      } else if (r.stale_cache) {
        message.warning(r.message || '刷新未取到新结果，已显示缓存列表。')
      } else if (currentSignature && currentSignature === previousSignature) {
        message.info('已刷新，但暂时没有新的推荐论文。')
      } else if (r.message) {
        message.success(`刷新完成：${r.message}`)
      } else {
        message.success('刷新完成')
      }
    }
  } catch (e: unknown) {
    skippedIds.value = previousSkipped
    message.error((e as Error).message || '请求失败')
    emptyHint.value = searchResults.value.length > 0
      ? '刷新失败，已保留当前列表。'
      : '加载失败，请检查网络与后端日志。'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}
onMounted(() => {
  loading.value = true
  void reloadDaily(false)
})
const saveOne = async (paper: Paper) => {
  try {
    const res = await savePapers([paper])
    const parts = [`已新增 ${res.added} 条` + ((res.updated ?? 0) > 0 ? `，已更新 ${res.updated} 条` : '')]
    if ((res.llm_classified ?? 0) > 0) parts.push(`LLM 归类 ${res.llm_classified} 条`)
    if ((res.pdf_downloaded ?? 0) > 0) parts.push(`本地 PDF ${res.pdf_downloaded} 个`)
    message.success(parts.join('，'))
    if (res.message) message.warning(res.message)
    const identityKey = paper.arxiv_id
      ? `arxiv:${paper.arxiv_id}`
      : paper.doi
        ? `doi:${paper.doi}`
        : `title_hash:${paper.title}_${paper.year}`
    void postDailyRecommendFeedback({
      identity_key: identityKey,
      title: paper.title,
      action: 'save',
      source_list: randomIds.value.has(paper.arxiv_id || '') ? 'general' : 'personalized',
      journal: (paper as any).journal,
      source: (paper as any).source,
    })
  } catch (e: unknown) {
    message.error((e as Error).message || '保存失败')
  }
}
function getPaperIdentityKey(paper: Paper): string {
  if (paper.arxiv_id) return `arxiv:${paper.arxiv_id}`
  if (paper.doi) return `doi:${paper.doi}`
  return `title_hash:${paper.title}_${paper.year}`
}
function hintFor(paper: Paper): { kind: string; explanation: string } | null {
  const k = getPaperIdentityKey(paper)
  return hintsMap.value.get(k) || null
}
async function ensureSavedAndOpenReader(paper: Paper) {
  const res = await savePapers([paper])
  const pid = (res.ids || [])[0]
  if (!pid) throw new Error('保存后未返回 paper_id')
  const identityKey = getPaperIdentityKey(paper)
  void postDailyRecommendFeedback({
    identity_key: identityKey,
    title: paper.title,
    action: 'read',
    source_list: randomIds.value.has(paper.arxiv_id || '') ? 'general' : 'personalized',
    journal: (paper as any).journal,
    source: (paper as any).source,
  })
  await router.push({ path: `/library/read/${pid}`, query: { standalone: '1' } })
}
function showWhyAndMaybeRead(paper: Paper) {
  const h = hintFor(paper)
  if (!h) return
  Modal.confirm({
    title: '为什么推荐这篇？',
    content: h.explanation || '（暂无解释）',
    okText: '去阅读',
    cancelText: '关闭',
    async onOk() {
      try {
        await ensureSavedAndOpenReader(paper)
      } catch (e: any) {
        message.error(e?.message || '跳转失败')
        throw e
      }
    },
  })
}
const skipOne = async (paper: Paper, index: number) => {
  const identityKey = getPaperIdentityKey(paper)
  searchResults.value.splice(index, 1)
  searchResults.value = [...searchResults.value]
  skippedIds.value.add(identityKey)
  try {
    await postDailyRecommendFeedback({
      identity_key: identityKey,
      title: paper.title,
      action: 'skip',
      source_list: randomIds.value.has(paper.arxiv_id || '') ? 'general' : 'personalized',
      keywords: paper.keywords,
      category: paper.category,
      journal: (paper as any).journal,
      source: (paper as any).source,
    })
    message.success('已标记为不感兴趣，后续将减少类似推荐')
  } catch (e: unknown) {
    console.warn('反馈记录失败:', e)
  }
}
const onPaperClick = async (paper: Paper) => {
  const identityKey = getPaperIdentityKey(paper)
  try {
    await postDailyRecommendFeedback({
      identity_key: identityKey,
      title: paper.title,
      action: 'click',
      source_list: randomIds.value.has(paper.arxiv_id || '') ? 'general' : 'personalized',
      journal: (paper as any).journal,
      source: (paper as any).source,
    })
  } catch (e) {
    console.warn('点击反馈记录失败:', e)
  }
}
</script>
<style scoped>
.daily-page {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  flex: 1 1 auto;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
.daily-toolbar {
  padding: 16px 18px;
  background: linear-gradient(160deg, #fafbfc 0%, #f3f5f7 55%, #f7f8fa 100%);
  border: 1px solid rgba(5,5,5,0.08);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  margin-bottom: 16px;
}
.daily-toolbar__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px 16px;
}
.daily-toolbar__left {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.daily-toolbar__headline {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
  color: rgba(0,0,0,0.82);
  word-break: break-word;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}
.daily-toolbar__headline :deep(.daily-toolbar__head-date-tag.ant-tag) {
  margin: 0;
  flex-shrink: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.35;
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
}
.daily-toolbar__head-core {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 8px;
  min-width: 0;
}
.daily-toolbar__head-kw {
  flex-shrink: 0;
  font-weight: 600;
  color: #1677ff;
}
.daily-toolbar__head-stats {
  font-weight: 500;
  font-size: 13px;
  color: rgba(0,0,0,0.58);
}
.daily-toolbar__head-strategy-more {
  margin: 8px 0 0;
  padding: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(0,0,0,0.72);
  white-space: pre-line;
}
.daily-toolbar__section {
  border-top: 1px solid rgba(5,5,5,0.07);
  margin-top: 14px;
  padding-top: 14px;
}
.daily-toolbar__section-head {
  font-size: 12px;
  font-weight: 600;
  color: rgba(0,0,0,0.48);
  margin-bottom: 8px;
}
.daily-toolbar__section--split-kw {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 20px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(5,5,5,0.07);
}
.daily-toolbar__section--split-kw:has(.daily-toolbar__kw-panel:only-child) {
  justify-content: flex-start;
}
.daily-toolbar__kw-panel {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  flex: 1 1 calc(50% - 10px);
  min-width: 0;
  max-width: calc(50% - 10px);
}
.daily-toolbar__kw-panel:only-child {
  flex: 1 1 100%;
  max-width: 100%;
}
.daily-toolbar__section--split-kw .daily-toolbar__kw-title {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 600;
  color: rgba(0,0,0,0.78);
  white-space: nowrap;
  line-height: 1.45;
}
.daily-toolbar__tag-row--kw {
  flex: 1 1 auto;
  min-width: 0;
  justify-content: flex-start;
}
@media (max-width: 640px) {
  .daily-toolbar__kw-panel {
  flex: 1 1 100%;
  max-width: 100%;
  }
}
.daily-toolbar__tag-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.daily-toolbar__tag-row :deep(.ant-tag) {
  margin-inline-end: 0;
  max-width: 100%;
}
.daily-toolbar__actions {
  justify-self: end;
  align-self: center;
}
@media (max-width: 576px) {
  .daily-toolbar__row {
  grid-template-columns: 1fr;
  }
  .daily-toolbar__actions {
  justify-self: end;
  }
}
.daily-page__empty {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
}
.daily-page__loading {
  flex: 1 1 auto;
  align-self: stretch;
  width: 100%;
  min-height: 220px;
  padding: 48px 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 14px;
}
.daily-page__loading :deep(.ant-spin) {
  display: inline-flex;
  line-height: 1;
}
.daily-page__loading-text {
  font-size: 15px;
  color: rgba(0,0,0,0.65);
  line-height: 1.4;
  user-select: none;
}
.daily-results-card {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  --ant-color-fill-alter: #fff;
  --ant-color-fill-secondary: #fff;
  --ant-color-fill-content: #fff;
  margin-top: 0;
}
.daily-results-card :deep(.ant-card) {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}
.daily-results-card :deep(.ant-card-body) {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow-x: visible;
  overflow-y: visible;
  padding: 16px;
}
.daily-results-card :deep(.daily-paper-list.ant-list) {
  flex: 1 1 auto;
}
.daily-results-card :deep(.ant-card-head) {
  border-bottom: 1px solid rgba(5,5,5,0.06);
}
.daily-results-card :deep(.daily-paper-list.ant-list .ant-list-item) {
  container-type: inline-size;
  container-name: daily-paper-row;
  align-items: flex-start;
  padding: 14px 0 !important;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-action) {
  margin-inline-start: 16px !important;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-action > li) {
  padding-inline: 4px 0;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-meta-description) {
  width: 100cqw;
  max-width: 100cqw;
  box-sizing: border-box;
}
@supports not (width: 1cqw) {
  .daily-results-card :deep(.daily-paper-list .ant-list-item-meta-description) {
  width: calc(100% + clamp(13rem, 36vw, 28rem));
  max-width: none;
  }
}
.daily-page__alert {
  margin-bottom: 16px;
}
.daily-results-card__hint {
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  max-width: 280px;
  text-align: right;
  line-height: 1.4;
}
@media (max-width: 576px) {
  .daily-results-card__hint {
  display: none;
  }
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-meta) {
  min-width: 0;
  flex: 1 1 0%;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-meta-content) {
  overflow: visible;
  min-width: 0;
  width: 100%;
  max-width: 100%;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-meta-title) {
  width: 100%;
  max-width: 100%;
  display: block;
  margin-bottom: 0 !important;
  padding-bottom: 2px;
}
.daily-results-card :deep(.daily-paper-list.ant-list,
.daily-paper-list .ant-spin-container,
.daily-paper-list .ant-list-items,
.daily-paper-list .ant-list-item,
.daily-paper-list .ant-list-item-meta,
.daily-paper-list .ant-list-item-meta-content) {
  background-color: #fff !important;
  background-image: none !important;
  transition: none !important;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item:hover,
.daily-paper-list .ant-list-item:focus,
.daily-paper-list .ant-list-item:focus-within,
.daily-paper-list .ant-list-item:active,
.daily-paper-list .ant-list-item-meta:hover,
.daily-paper-list .ant-list-item-meta-content:hover) {
  background-color: #fff !important;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item-meta-title:hover) {
  background-color: transparent !important;
}
.daily-results-card :deep(.daily-paper-list .ant-pagination) {
  background-color: #fff !important;
}
.daily-results-card :deep(.daily-paper-list .ant-list-item:last-child) {
  border-bottom: none;
}
</style>
