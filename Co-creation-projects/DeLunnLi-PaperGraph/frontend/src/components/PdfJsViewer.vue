<template>
  <div class="pdf-viewer">
    <div class="pdf-toolbar">
      <div class="pdf-toolbar__group">
        <a-button size="small" :disabled="loading || currentPage <= 1" @click="gotoPage(currentPage - 1)">上一页</a-button>
        <a-input-number v-model:value="pageInput" size="small" aria-label="页码" :min="1" :max="pageCount || 1"
          :disabled="loading || !pageCount" @press-enter="applyPageInput" @blur="applyPageInput" />
        <span>/ {{ pageCount || '—' }} 页</span>
        <a-button size="small" :disabled="loading || currentPage >= pageCount" @click="gotoPage(currentPage + 1)">下一页</a-button>
      </div>
      <div class="pdf-toolbar__group">
        <a-button size="small" aria-label="缩小" :disabled="loading || !pageCount || scale <= 0.5" @click="changeZoom(-0.15)">−</a-button>
        <span>{{ Math.round(scale * 100) }}%</span>
        <a-button size="small" aria-label="放大" :disabled="loading || !pageCount || scale >= 2.5" @click="changeZoom(0.15)">＋</a-button>
        <a-button size="small" :disabled="loading || !pageCount" @click="fitWidth">适应宽度</a-button>
      </div>
    </div>
    <div ref="stageRef" class="pdf-stage" :aria-busy="loading">
      <div v-if="loading" class="pdf-state"><a-spin tip="正在加载论文 PDF…" /></div>
      <div v-if="error" class="pdf-state pdf-error" role="alert">
        <span>{{ error }}</span>
        <a-button size="small" @click="loadDocument">重新加载</a-button>
      </div>
      <div v-show="pageCount && !loading && !error" class="pdf-page" :style="{ '--scale-factor': scale }">
        <canvas ref="canvasRef" class="pdf-canvas" :aria-label="`PDF 第 ${currentPage} 页`" />
        <div ref="textLayerRef" class="textLayer" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask, TextLayer } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import 'pdfjs-dist/web/pdf_viewer.css'
import { BACKEND_ORIGIN } from '../config/ports'

const props = withDefaults(defineProps<{ src: string; page?: number }>(), { page: 1 })
const emit = defineEmits<{ loaded: []; error: [message: string] }>()
const stageRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const textLayerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const error = ref('')
const pageCount = ref(0)
const currentPage = ref(1)
const pageInput = ref<number | null>(1)
const scale = ref(1.15)
let pdfjs: typeof import('pdfjs-dist')
let pdfDocument: PDFDocumentProxy | null = null
let loadingTask: PDFDocumentLoadingTask | null = null
let renderTask: RenderTask | null = null
let textLayer: TextLayer | null = null
let loadGeneration = 0
let renderGeneration = 0
let loadedEmitted = false

const normalizePage = (page: number | null) => Math.max(1, Math.min(pageCount.value || 1, Math.floor(Number(page) || 1)))
const reportError = (cause: unknown) => {
  error.value = `PDF 加载失败：${cause instanceof Error ? cause.message : '文件不可用'}`
  emit('error', error.value)
}
const cancelRender = () => {
  renderGeneration += 1
  renderTask?.cancel()
  textLayer?.cancel()
  textLayer = null
}
const disposeDocument = () => {
  cancelRender()
  // The loading task owns the worker and document, so destroy it only once.
  const previous = loadingTask
  loadingTask = null
  pdfDocument = null
  void previous?.destroy().catch(() => {})
}

const renderPage = async () => {
  const document = pdfDocument
  if (!document) return
  const previousRender = renderTask
  cancelRender()
  const generation = renderGeneration
  const pageNumber = currentPage.value
  const pageScale = scale.value
  loading.value = true
  error.value = ''
  try {
    // PDF.js cannot render two tasks into the same canvas at the same time.
    await previousRender?.promise.catch(() => {})
    const page = await document.getPage(pageNumber)
    if (generation !== renderGeneration) return
    await nextTick()
    const canvas = canvasRef.value
    const container = textLayerRef.value
    if (!canvas || !container) return
    const viewport = page.getViewport({ scale: pageScale })
    const ratio = Math.min(2, Math.max(1, window.devicePixelRatio || 1))
    canvas.width = Math.ceil(viewport.width * ratio)
    canvas.height = Math.ceil(viewport.height * ratio)
    canvas.style.width = `${viewport.width}px`
    canvas.style.height = `${viewport.height}px`
    container.replaceChildren()
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器无法创建 PDF 画布')
    const task = page.render({ canvasContext: context, viewport, transform: [ratio, 0, 0, ratio, 0, 0] })
    renderTask = task
    await task.promise
    if (generation !== renderGeneration) return
    const textContent = await page.getTextContent()
    if (generation !== renderGeneration) return
    const layer = new pdfjs.TextLayer({ textContentSource: textContent, container, viewport })
    textLayer = layer
    await layer.render()
    if (generation !== renderGeneration) return
    if (!loadedEmitted) {
      loadedEmitted = true
      emit('loaded')
    }
  } catch (cause) {
    if (generation === renderGeneration) reportError(cause)
  } finally {
    if (generation === renderGeneration) {
      renderTask = null
      loading.value = false
    }
  }
}

const loadDocument = async () => {
  const generation = ++loadGeneration
  disposeDocument()
  loading.value = false
  error.value = ''
  pageCount.value = 0
  loadedEmitted = false
  const src = props.src.trim()
  if (!src) return
  loading.value = true
  try {
    const url = new URL(src, window.location.origin)
    const backendOrigin = new URL(BACKEND_ORIGIN || window.location.origin, window.location.origin).origin
    if (!['http:', 'https:'].includes(url.protocol) || ![window.location.origin, backendOrigin].includes(url.origin)) {
      throw new Error('仅允许加载本站或已配置后端的 PDF')
    }
    pdfjs = await import('pdfjs-dist')
    if (generation !== loadGeneration) return
    pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
    const assetBase = `${import.meta.env.BASE_URL}pdfjs/`
    const task = pdfjs.getDocument({
      url: url.href,
      withCredentials: false,
      cMapUrl: `${assetBase}cmaps/`,
      cMapPacked: true,
      standardFontDataUrl: `${assetBase}standard_fonts/`,
    })
    loadingTask = task
    const document = await task.promise
    if (generation !== loadGeneration) return
    pdfDocument = document
    pageCount.value = document.numPages
    currentPage.value = normalizePage(props.page)
    pageInput.value = currentPage.value
    await renderPage()
  } catch (cause) {
    if (generation !== loadGeneration) return
    loading.value = false
    reportError(cause)
  }
}
const gotoPage = async (page: number | null) => {
  const target = normalizePage(page)
  pageInput.value = target
  if (!pdfDocument || target === currentPage.value) return
  currentPage.value = target
  stageRef.value?.scrollTo({ top: 0, left: 0 })
  await renderPage()
}
const applyPageInput = () => void gotoPage(pageInput.value)
const changeZoom = async (delta: number) => {
  scale.value = Math.max(0.5, Math.min(2.5, Number((scale.value + delta).toFixed(2))))
  await renderPage()
}
const fitWidth = async () => {
  const document = pdfDocument
  if (!document || !stageRef.value) return
  const generation = renderGeneration
  try {
    const page = await document.getPage(currentPage.value)
    if (generation !== renderGeneration || !stageRef.value) return
    const width = page.getViewport({ scale: 1 }).width
    scale.value = Math.max(0.5, Math.min(2.5, (stageRef.value.clientWidth - 40) / width))
    await renderPage()
  } catch (cause) {
    if (generation === renderGeneration) reportError(cause)
  }
}
defineExpose({ gotoPage })
watch(() => props.src, () => void loadDocument(), { immediate: true })
watch(() => props.page, (page) => void gotoPage(page))
onBeforeUnmount(() => {
  loadGeneration += 1
  disposeDocument()
})
</script>
<style scoped>
.pdf-viewer { width: 100%; height: 100%; min-height: 0; display: flex; flex-direction: column; background: #e5e7eb; }
.pdf-toolbar { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 10px 12px; background: #fff; border-bottom: 1px solid #ddd; }
.pdf-toolbar__group { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.pdf-toolbar :deep(.ant-input-number) { width: 60px; }
.pdf-stage { flex: 1; min-height: 0; overflow: auto; padding: 20px; }
.pdf-page { position: relative; width: fit-content; margin: 0 auto; background: #fff; box-shadow: 0 2px 12px #0002; }
.pdf-canvas { display: block; }
.pdf-state { min-height: 100%; display: flex; align-items: center; justify-content: center; gap: 12px; }
.pdf-error { flex-direction: column; color: #cf1322; text-align: center; }
</style>
