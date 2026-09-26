<template>
  <div class="paper-reader">
    <div class="paper-reader__toolbar">
      <a-space>
        <a-button type="link" @click="backToLibrary">← 返回文献库</a-button>
        <a-button v-if="isStandalone" type="link" @click="closeTab">关闭</a-button>
      </a-space>
      <span v-if="paper" class="paper-reader__title">{{ paper.title }}</span>
      <span v-else class="paper-reader__title paper-reader__title--placeholder">文献阅读</span>
    </div>
    <div v-if="loadError" class="paper-reader__err">{{ loadError }}</div>
    <div v-if="pdfParsing" class="paper-reader__notice">PDF 正在解析中，论文全文内容将在稍后可用。你可先基于摘要提问。</div>
    <div ref="splitRef" class="paper-reader__split">
      <div class="paper-reader__pane paper-reader__pane--pdf" :style="leftPaneStyle">
        <PdfJsViewer
          v-if="paperId != null && pdfSrc"
          :src="pdfSrc"
          @loaded="onPdfLoaded"
          @error="onPdfError"
          class="pdf-js-viewer-wrapper"
        />
        <a-empty
          v-else
          :description="
            loadingPaper
              ? '正在加载文献信息…'
              : '该文献尚无本地 PDF（可能无可用下载链接，或上次保存时下载失败）。可基于摘要与助手对话；可回检索/文献库重新保存以重试下载。'
          "
        />
      </div>
      <div
        ref="dividerRef"
        class="paper-reader__divider"
        role="separator"
        aria-label="Resize"
        @pointerdown="onDividerPointerDown"
      />
      <div class="paper-reader__pane paper-reader__pane--chat" :style="rightPaneStyle">
        <div
          ref="scrollRef"
          class="paper-reader__messages"
          @wheel.stop="onChatWheel"
          @scroll.stop
        >
          <div v-if="loadingPaper && messages.length === 0" class="paper-reader__msg paper-reader__msg--assistant">
            <div class="paper-reader__msg-role">论文阅读助手</div>
            <div class="paper-reader__msg-body">正在后台加载文献与导读，你可以先输入问题。</div>
          </div>
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="paper-reader__msg"
            :class="'paper-reader__msg--' + m.role"
          >
            <div class="paper-reader__msg-role">{{ m.role === 'user' ? '你' : '论文阅读助手' }}</div>
            <div v-if="m.role === 'user'" class="paper-reader__msg-body">{{ m.content }}</div>
            <div v-else class="paper-reader__msg-body" v-html="renderMarkdown(normalizeAssistantText(m.content))"></div>
            <div v-if="m.role === 'assistant' && m.related_papers && m.related_papers.length" class="paper-reader__related">
              <div class="paper-reader__related-title">推荐论文</div>
              <ul class="paper-reader__related-cards">
                <li v-for="(item, index) in m.related_papers" :key="index" class="paper-reader__related-card">
                  <div class="paper-reader__related-card-head">
                    <span class="paper-reader__related-idx">{{ index + 1 }}.</span>
                    <a
                      v-if="paperExternalUrl(item)"
                      class="paper-reader__related-title-link"
                      :href="paperExternalUrl(item)!"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click.stop
                    >
                      {{ item.title || '（无标题）' }}
                    </a>
                    <span v-else class="paper-reader__related-title-link paper-reader__related-title-link--text">
                      {{ item.title || '（无标题）' }}
                    </span>
                  </div>
                  <div v-if="relatedPaperMetaLine(item)" class="paper-reader__related-card-meta">
                    {{ relatedPaperMetaLine(item) }}
                  </div>
                  <div class="paper-reader__related-card-actions">
                    <a-button
                      v-if="paperExternalUrl(item)"
                      type="link"
                      size="small"
                      class="paper-reader__related-act"
                      :href="paperExternalUrl(item)!"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click.stop
                    >
                      打开链接
                    </a-button>
                    <a-button
                      type="primary"
                      size="small"
                      ghost
                      class="paper-reader__related-act"
                      @click.stop="saveRelatedPaperToLibrary(item)"
                    >
                      保存到库
                    </a-button>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div class="paper-reader__input">
          <a-textarea
            :key="inputKey"
            v-model:value="draft"
            :rows="1"
            :auto-size="{ minRows: 1, maxRows: 6 }"
            placeholder="基于当前文献提问…"
            :disabled="sending"
            @compositionstart="composing = true"
            @compositionend="composing = false"
            @press-enter.exact.prevent="send"
          />
          <a-button type="primary" :loading="sending" :disabled="!draft.trim()" @click="send">发送</a-button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  getPaper,
  getLibraryPdfHref,
  postPaperReaderOpening,
  postPaperReaderChat,
  getPaperReaderHistory,
  postReadingLog,
  savePapers,
} from '@/services/api'
import type { Paper } from '@/types'
import PdfJsViewer from '@/components/PdfJsViewer.vue'
import { renderMarkdown } from '@/utils/markdown'
const route = useRoute()
const router = useRouter()
const paper = ref<Paper | null>(null)
const loadingPaper = ref(true)
const loadError = ref('')
const pdfParsing = ref(false)
const messages = ref<
  {
    role: 'user' | 'assistant'
    content: string
    related_papers?: Paper[]
  }[]
>([])
const draft = ref('')
const sending = ref(false)
const composing = ref(false)
const inputKey = ref(0)
const scrollRef = ref<HTMLElement | null>(null)
const splitRef = ref<HTMLElement | null>(null)
const dividerRef = ref<HTMLElement | null>(null)
const leftWidthPx = ref<number | null>(null)
const dragging = ref(false)
const dragPointerId = ref<number | null>(null)
const rafPending = ref(false)
const lastClientX = ref<number | null>(null)
const readingSession = ref<{ paperId: number; startedAtMs: number } | null>(null)
const normalizeAssistantText = (s: string): string => {
  const raw = String(s || '')
  if (raw.includes('```')) return raw.replace(/\r\n/g, '\n')
  return raw
    .replace(/\r\n/g, '\n')
    .replace(/^[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
const paperId = computed(() => {
  const raw = route.params.id
  const n = typeof raw === 'string' ? parseInt(raw, 10) : Array.isArray(raw) ? parseInt(raw[0], 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : null
})
const isStandalone = computed(() => String(route.query?.standalone || '') === '1')
const hasLocalPdfForViewer = computed(
  () => !!(paper.value?.local_pdf_path && String(paper.value.local_pdf_path).trim())
)
const pdfSrc = computed(() => {
  if (paperId.value == null) return ''
  return hasLocalPdfForViewer.value ? getLibraryPdfHref(paperId.value) : ''
})
const onPdfError = (msg: string) => {
  loadError.value = msg || 'PDF 加载失败'
  pdfReady.value = true
  void maybeStartOpening()
}
const pdfReady = ref(false)
const openingStarted = ref(false)
const onPdfLoaded = () => {
  pdfReady.value = true
  void maybeStartOpening()
}
const leftPaneStyle = computed(() => {
  if (leftWidthPx.value == null) return {}
  return { flex: `0 0 ${leftWidthPx.value}px` }
})
const rightPaneStyle = computed(() => ({}))
const backToLibrary = () => {
  router.push('/library')
}
const closeTab = () => {
  try {
    window.close()
  } catch {
  }
}
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
const onChatWheel = (e: WheelEvent) => {
  e.stopPropagation()
}
const initDefaultSplitIfNeeded = () => {
  if (leftWidthPx.value != null) return
  const el = splitRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  if (!Number.isFinite(rect.width) || rect.width <= 0) return
  const desiredLeft = rect.width * 0.8
  const minSide = 320
  const maxLeft = Math.max(minSide, rect.width - minSide)
  leftWidthPx.value = clamp(Math.round(desiredLeft), minSide, maxLeft)
}
const setLeftWidthFromClientX = (clientX: number) => {
  const el = splitRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const minSide = 320
  const maxLeft = Math.max(minSide, rect.width - minSide)
  const w = clamp(clientX - rect.left, minSide, maxLeft)
  leftWidthPx.value = w
}
const scheduleDragUpdate = () => {
  if (rafPending.value) return
  rafPending.value = true
  requestAnimationFrame(() => {
    rafPending.value = false
    if (!dragging.value) return
    if (lastClientX.value == null) return
    setLeftWidthFromClientX(lastClientX.value)
  })
}
const onDividerPointerMove = (ev: PointerEvent) => {
  if (!dragging.value) return
  if (dragPointerId.value != null && ev.pointerId !== dragPointerId.value) return
  lastClientX.value = ev.clientX
  scheduleDragUpdate()
}
const endDrag = () => {
  if (!dragging.value) return
  dragging.value = false
  dragPointerId.value = null
  lastClientX.value = null
  rafPending.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', onDividerPointerMove)
  window.removeEventListener('pointerup', onDividerPointerUp)
  window.removeEventListener('pointercancel', onDividerPointerUp)
}
const onDividerPointerUp = (ev: PointerEvent) => {
  if (dragPointerId.value != null && ev.pointerId !== dragPointerId.value) return
  endDrag()
}
const onDividerPointerDown = (ev: PointerEvent) => {
  if (ev.button !== 0) return
  ev.preventDefault()
  dragging.value = true
  dragPointerId.value = ev.pointerId
  lastClientX.value = ev.clientX
  setLeftWidthFromClientX(ev.clientX)
  try {
    dividerRef.value?.setPointerCapture(ev.pointerId)
  } catch {
  }
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onDividerPointerMove)
  window.addEventListener('pointerup', onDividerPointerUp)
  window.addEventListener('pointercancel', onDividerPointerUp)
}
onBeforeUnmount(() => {
  endDrag()
  void flushReadingSession()
})
const flushReadingSession = async () => {
  const s = readingSession.value
  if (!s) return
  readingSession.value = null
  const durMs = Date.now() - s.startedAtMs
  const sec = Math.floor(durMs / 1000)
  if (!Number.isFinite(sec) || sec < 8) return
  try {
    await postReadingLog({ paper_id: s.paperId, duration_sec: Math.min(sec, 60 * 60 * 6), client_ts: Math.floor(Date.now() / 1000) })
  } catch {
  }
}
const scrollBottom = async () => {
  await nextTick()
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}
const mapHistoryTurns = (
  turns: { role?: string; content?: string | null; created_at?: number }[]
): { role: 'user' | 'assistant'; content: string; related_papers?: Paper[] }[] =>
  turns
    .filter((t) => t && (t.role === 'user' || t.role === 'assistant') && String(t.content || '').trim())
    .map((t) => {
      const role = t.role as 'user' | 'assistant'
      const content = role === 'assistant' ? normalizeAssistantText(String(t.content)) : String(t.content)
      return { role, content }
    })
const ensureOpeningAndHistory = async (reloadHistory = false, showError = true) => {
  if (paperId.value == null) return
  try {
    const res = await postPaperReaderOpening(paperId.value)
    if (!res.success || !res.opening) return
    if (res.pdf_parsing) pdfParsing.value = true
    if (reloadHistory) {
      const h = await getPaperReaderHistory(paperId.value, 200)
      if (h?.success && Array.isArray(h.turns) && h.turns.length > 0) {
        const restored = mapHistoryTurns(h.turns)
        if (restored.length > 0) {
          messages.value = restored
          await scrollBottom()
          return
        }
      }
    }
    const hasAssistantMessage = messages.value.some((m) => m.role === 'assistant')
    if (!hasAssistantMessage) {
      messages.value.push({ role: 'assistant', content: normalizeAssistantText(res.opening) })
      await scrollBottom()
    }
  } catch (e: unknown) {
    if (showError) {
      message.error((e as Error).message || '导读加载失败')
    }
  }
}
const maybeStartOpening = async (reloadHistory = false, showError = true) => {
  if (openingStarted.value) return
  if (paperId.value == null) return
  if (hasLocalPdfForViewer.value && !pdfReady.value) return
  openingStarted.value = true
  void ensureOpeningAndHistory(reloadHistory, showError)
}
const send = async () => {
  const text = draft.value.trim()
  if (!text || paperId.value == null || sending.value) return
  if (composing.value) return
  sending.value = true
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  inputKey.value += 1
  await nextTick()
  await scrollBottom()
  try {
    const res = await postPaperReaderChat({
      paper_id: paperId.value,
      messages: messages.value.slice(0, -1),
      user_message: text,
    })
    if (res.success && res.reply) {
      const rp = Array.isArray((res as any).related_papers) ? ((res as any).related_papers as Paper[]) : []
      messages.value.push({
        role: 'assistant',
        content: normalizeAssistantText(res.reply),
        related_papers: rp.length ? rp : undefined,
      })
    } else {
      messages.value.push({ role: 'assistant', content: '（无回复）' })
    }
  } catch (e: unknown) {
    message.error((e as Error).message || '发送失败')
    messages.value.push({ role: 'assistant', content: '请求失败，请检查网络或 LLM 配置。' })
  } finally {
    sending.value = false
    await scrollBottom()
  }
}
const paperExternalUrl = (p: Paper): string | null => {
  if (!p) return null
  const src = String(p.source_url || '').trim()
  if (src && /^https?:\/\//i.test(src)) return src
  const pdf = String(p.pdf_url || '').trim()
  if (pdf && /^https?:\/\//i.test(pdf)) return pdf
  let ax = String(p.arxiv_id || '').trim()
  if (ax) {
    ax = ax.replace(/^arxiv:/i, '').replace(/\.pdf$/i, '')
    return `https://arxiv.org/abs/${ax}`
  }
  const doiRaw = String(p.doi || '').trim()
  if (doiRaw) {
    if (/^https?:\/\//i.test(doiRaw)) return doiRaw
    return `https://doi.org/${doiRaw.replace(/^doi:/i, '')}`
  }
  return null
}
const relatedPaperMetaLine = (p: Paper): string => {
  const parts: string[] = []
  const names = (p.authors || []).map((a: { name?: string }) => a?.name).filter(Boolean) as string[]
  if (names.length) parts.push(names.slice(0, 4).join(', ') + (names.length > 4 ? '…' : ''))
  if (p.year != null) parts.push(String(p.year))
  const j = String((p as { journal?: string }).journal || (p as { venue?: string }).venue || '').trim()
  if (j) parts.push(j)
  let s = parts.join(' · ')
  if (s.length > 140) s = `${s.slice(0, 137)}…`
  return s
}
const saveRelatedPaperToLibrary = async (p: Paper) => {
  if (!p) return
  try {
    await savePapers([p], { llm_classify: false })
    message.success('已保存到文献库')
  } catch (e: unknown) {
    message.error((e as Error).message || '保存失败')
  }
}
const loadPaper = async () => {
  await flushReadingSession()
  loadingPaper.value = true
  loadError.value = ''
  paper.value = null
  pdfReady.value = false
  openingStarted.value = false
  messages.value = []
  await nextTick()
  initDefaultSplitIfNeeded()
  if (paperId.value == null) {
    loadError.value = '无效的文献 ID'
    loadingPaper.value = false
    return
  }
  readingSession.value = { paperId: paperId.value, startedAtMs: Date.now() }
  try {
    paper.value = await getPaper(paperId.value)
    try {
      const h = await getPaperReaderHistory(paperId.value, 200)
      if (h?.success && Array.isArray(h.turns) && h.turns.length > 0) {
        const restored = mapHistoryTurns(h.turns)
        if (restored.length > 0) {
          messages.value = restored
          await scrollBottom()
        }
      }
    } catch {
    }
    if (messages.value.length === 0) {
      void maybeStartOpening()
    } else if (messages.value[0]?.role === 'user') {
      void maybeStartOpening(true, false)
    }
  } catch (e: unknown) {
    loadError.value = (e as Error).message || '加载失败'
  } finally {
    loadingPaper.value = false
  }
}
watch(
  () => route.params.id,
  () => {
    void loadPaper()
  },
  { immediate: true }
)
onMounted(() => {
  initDefaultSplitIfNeeded()
})
</script>
<style scoped>
.paper-reader {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100vh;
  color-scheme: light;
}
.paper-reader__toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.paper-reader__title--placeholder {
  color: rgba(0,0,0,0.45);
  font-weight: 500;
}
.paper-reader__title {
  flex: 1;
  min-width: 120px;
  font-weight: 600;
  font-size: 15px;
  color: rgba(0,0,0,0.85);
}
.paper-reader__err {
  color: #cf1322;
  padding: 16px;
}
.paper-reader__split {
  display: flex;
  flex-direction: row;
  flex: 1;
  min-height: 0;
  height: calc(100vh - 56px);
}
.paper-reader__pane {
  flex: 1;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
.paper-reader__pane--pdf {
  min-height: 0;
}
.paper-reader__divider {
  flex: 0 0 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  touch-action: none;
}
.paper-reader__divider::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(0,0,0,0.08);
}
.paper-reader__divider:hover::before {
  background: rgba(0,0,0,0.16);
}
.pdf-js-viewer-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.paper-reader__pane--chat {
  min-height: 0;
  max-height: calc(100vh - 56px);
  position: relative;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  overflow: hidden;
}
.paper-reader__messages {
  flex: 1;
  min-height: 0;
  max-height: calc(100vh - 56px - 60px - 16px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px;
  background: #f8f9fa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin: 8px;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: #1890ff transparent;
}
.paper-reader__messages::-webkit-scrollbar {
  width: 8px;
}
.paper-reader__messages::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 4px;
}
.paper-reader__messages::-webkit-scrollbar-thumb {
  background: #1890ff;
  border-radius: 4px;
  border: 2px solid #f0f0f0;
}
.paper-reader__messages::-webkit-scrollbar-thumb:hover {
  background: #40a9ff;
}
.paper-reader__messages::-webkit-scrollbar-button {
  display: none;
}
.paper-reader__msg {
  margin-bottom: 14px;
}
.paper-reader__msg-role {
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  margin-bottom: 4px;
}
.paper-reader__msg-body {
  line-height: 1.55;
  font-size: 14px;
  color: rgba(0,0,0,0.88);
}
.paper-reader__msg--user .paper-reader__msg-body {
  white-space: pre-wrap;
}
.paper-reader__msg-body :deep(h1),
.paper-reader__msg-body :deep(h2),
.paper-reader__msg-body :deep(h3) {
  margin: 10px 0 6px;
  line-height: 1.25;
}
.paper-reader__msg-body :deep(h1) {
  font-size: 18px;
}
.paper-reader__msg-body :deep(h2) {
  font-size: 16px;
}
.paper-reader__msg-body :deep(h4),
.paper-reader__msg-body :deep(h5),
.paper-reader__msg-body :deep(h6) {
  margin: 8px 0 4px;
  line-height: 1.3;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0,0,0,0.85);
}
.paper-reader__msg-body :deep(hr) {
  border: none;
  border-top: 1px solid rgba(0,0,0,0.1);
  margin: 12px 0;
}
.paper-reader__msg-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 13px;
  line-height: 1.45;
  display: block;
  overflow-x: auto;
  max-width: 100%;
  -webkit-overflow-scrolling: touch;
}
.paper-reader__msg-body :deep(thead th) {
  background: rgba(0,0,0,0.04);
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
}
.paper-reader__msg-body :deep(th),
.paper-reader__msg-body :deep(td) {
  border: 1px solid rgba(0,0,0,0.1);
  padding: 6px 8px;
  vertical-align: top;
  word-break: break-word;
}
.paper-reader__msg-body :deep(tbody tr:nth-child(even)) {
  background: rgba(0,0,0,0.02);
}
.paper-reader__msg-body :deep(ul),
.paper-reader__msg-body :deep(ol) {
  margin: 4px 0 4px 18px;
  padding: 0;
}
.paper-reader__msg-body :deep(li) {
  margin: 2px 0;
}
.paper-reader__msg-body :deep(code) {
  background: rgba(0,0,0,0.06);
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 12px;
}
.paper-reader__msg-body :deep(pre) {
  background: rgba(0,0,0,0.06);
  border-radius: 8px;
  padding: 10px;
  overflow: auto;
  margin: 8px 0;
}
.paper-reader__msg-body :deep(pre code) {
  background: transparent;
  padding: 0;
}
.paper-reader__msg--user .paper-reader__msg-body {
  background: #e6f4ff;
  padding: 8px 10px;
  border-radius: 8px;
}
.paper-reader__msg--assistant .paper-reader__msg-body {
  background: #f5f5f5;
  padding: 8px 10px;
  border-radius: 8px;
}
.paper-reader__related {
  border-top: 1px solid rgba(0,0,0,0.08);
  margin-top: 10px;
  padding-top: 10px;
}
.paper-reader__related-title {
  font-size: 12px;
  color: rgba(0,0,0,0.62);
  margin-bottom: 8px;
}
.paper-reader__related-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.paper-reader__related-card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 8px;
  padding: 8px 10px;
  background: #fafafa;
}
.paper-reader__related-card-head {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  line-height: 1.4;
}
.paper-reader__related-idx {
  flex-shrink: 0;
  color: rgba(0,0,0,0.45);
  font-size: 12px;
  line-height: 1.4;
}
.paper-reader__related-title-link {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: #1677ff;
  text-decoration: none;
  word-break: break-word;
}
.paper-reader__related-title-link:hover {
  text-decoration: underline;
}
.paper-reader__related-title-link--text {
  color: rgba(0,0,0,0.88);
  cursor: default;
}
.paper-reader__related-card-meta {
  color: rgba(0,0,0,0.58);
  font-size: 12px;
  line-height: 1.35;
  margin-top: 4px;
  padding-left: 1.5em;
}
.paper-reader__related-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: center;
  margin-top: 8px;
  padding-left: 1.5em;
}
.paper-reader__related-act.ant-btn-sm {
  height: auto;
  line-height: 1.35;
}
.paper-reader__input {
  display: flex;
  gap: 8px;
  padding: 10px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  align-items: center;
}
.paper-reader__input :deep(.ant-input) {
  flex: 1;
}
.paper-reader__input :deep(textarea.ant-input) {
  min-height: 32px;
  height: 32px;
  line-height: 22px;
  resize: none;
  padding-top: 4px;
  padding-bottom: 4px;
}
@media (max-width: 900px) {
  .paper-reader__split {
  flex-direction: column;
  gap: 12px;
  }
  .paper-reader__divider {
  display: none;
  }
}
</style>