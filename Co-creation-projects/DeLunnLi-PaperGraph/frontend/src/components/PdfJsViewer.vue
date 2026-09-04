<template>
  <div class="pdf-viewer">
    <iframe
      v-if="viewerUrl"
      :src="viewerUrl"
      class="pdf-iframe"
      frameborder="0"
      allowfullscreen
      @load="onIframeLoad"
      @error="onIframeError"
    />
    <div v-else-if="loading" class="pdf-loading">
      <a-spin tip="加载 PDF 中…" />
    </div>
    <div v-else-if="error" class="pdf-error">{{ error }}</div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
const props = defineProps<{ src: string }>()
const emit = defineEmits<{ loaded: []; error: [message: string] }>()
const viewerUrl = ref('')
const loading = ref(false)
const error = ref('')
const viewerPath = '/pdfjs/web/viewer.html'
const loadPdf = async () => {
  if (!props.src) return
  loading.value = true; error.value = ''
  try {
    viewerUrl.value = `${viewerPath}?file=${encodeURIComponent(props.src)}`
  } catch (e) {
    error.value = 'PDF 加载失败: ' + (e as Error).message
    loading.value = false; emit('error', error.value)
  }
}
const onIframeLoad = () => { loading.value = false; emit('loaded') }
const onIframeError = () => { error.value = 'PDF 加载失败'; loading.value = false; emit('error', error.value) }
watch(() => props.src, loadPdf, { immediate: true })
</script>
<style scoped>
.pdf-viewer { width: 100%; height: 100%; background: #f5f5f5; }
.pdf-iframe { width: 100%; height: 100%; border: none; display: block; }
.pdf-loading, .pdf-error { display: flex; align-items: center; justify-content: center; height: 100%; color: #666; }
.pdf-error { color: #cf1322; }
</style>