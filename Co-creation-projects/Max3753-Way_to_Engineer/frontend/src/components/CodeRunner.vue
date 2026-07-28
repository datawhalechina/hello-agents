<template>
  <div class="code-runner" :class="{ running, hasOutput: output !== null }">
    <!-- Header -->
    <div class="cr-header">
      <span class="cr-lang">{{ language }}</span>
      <button class="cr-run-btn" :disabled="running" @click="runCode">
        <span v-if="!running" class="run-icon">▶</span>
        <span v-else class="spinner"></span>
        {{ running ? '运行中...' : '运行' }}
      </button>
    </div>

    <!-- Code: highlighted read-only -->
    <pre class="cr-code"><code v-html="highlightedCode"></code></pre>

    <!-- Iframe preview for HTML/CSS -->
    <Transition name="slide">
      <div v-if="isHtmlLike && iframeSrc !== null" class="cr-output cr-iframe-output">
        <div class="output-header">
          <span class="output-label">✓ 预览</span>
          <button class="output-close" @click="iframeSrc = null">✕</button>
        </div>
        <iframe class="preview-iframe" :srcdoc="iframeSrc" sandbox="allow-scripts"></iframe>
      </div>
    </Transition>

    <!-- Output for backend-executed languages -->
    <Transition name="slide">
      <div v-if="!isHtmlLike && output !== null" class="cr-output" :class="{ error: !success }">
        <div class="output-header">
          <span class="output-label">{{ success ? '✓ 输出' : '✗ 错误' }}</span>
          <button class="output-close" @click="output = null">✕</button>
        </div>
        <pre class="output-content"><code>{{ output }}</code></pre>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import hljs from 'highlight.js'
import axios from 'axios'

const props = withDefaults(defineProps<{
  code: string
  language?: string
}>(), {
  language: 'python',
})

const running = ref(false)
const output = ref<string | null>(null)
const success = ref(true)
const iframeSrc = ref<string | null>(null)

const isHtmlLike = computed(() => props.language === 'html' || props.language === 'css')

const highlightedCode = computed(() => {
  try {
    if (props.language && hljs.getLanguage(props.language)) {
      return hljs.highlight(props.code, { language: props.language }).value
    }
    return hljs.highlightAuto(props.code).value
  } catch {
    return escapeHtml(props.code)
  }
})

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch: string) => {
    const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
    return map[ch] || ch
  })
}

async function runCode() {
  if (running.value) return
  running.value = true
  output.value = null
  iframeSrc.value = null

  // HTML/CSS: render in iframe directly (no backend call)
  if (isHtmlLike.value) {
    if (props.language === 'html') {
      iframeSrc.value = props.code
    } else if (props.language === 'css') {
      iframeSrc.value = `<!DOCTYPE html>
<html>
<head>
  <style>${props.code}</style>
</head>
<body>
  <div class="preview-content" style="font-family:sans-serif;padding:20px;">
    <h1>CSS 预览</h1>
    <p>你的样式已应用到此页面。</p>
  </div>
</body>
</html>`
    }
    running.value = false
    return
  }

  // Backend execution for other languages
  try {
    const res = await axios.post('/api/code/execute', {
      code: props.code,
      language: props.language,
    })
    success.value = res.data.success
    output.value = res.data.output || res.data.error || '(无输出)'
  } catch (err: any) {
    success.value = false
    output.value = err.response?.data?.detail || err.message || '请求失败'
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.code-runner {
  margin: 12px 0;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  overflow: hidden;
  background: #1e1e1e;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
}

.cr-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #2d2d2d;
  border-bottom: 1px solid #3a3a3a;
}

.cr-lang {
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.cr-run-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: #fff;
  background: #2ea043;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.cr-run-btn:hover:not(:disabled) {
  background: #2c974b;
  transform: translateY(-1px);
}

.cr-run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.run-icon {
  font-size: 10px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.cr-code {
  margin: 0;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  color: #c9d1d9;
}

.cr-code :deep(code) {
  font-family: inherit;
}

/* Output */
.cr-output {
  border-top: 1px solid #3a3a3a;
  background: #0d1117;
}

.cr-output.error {
  border-top-color: #5a1d1d;
}

.output-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #161b22;
}

.output-label {
  font-size: 11px;
  font-weight: 600;
  color: #7ee787;
}

.cr-output.error .output-label {
  color: #ff7b72;
}

.output-close {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}

.output-close:hover {
  color: #fff;
  background: rgba(255,255,255,0.1);
}

.output-content {
  margin: 0;
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.5;
  color: #c9d1d9;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Iframe output */
.cr-iframe-output {
  padding: 0;
}

.preview-iframe {
  width: 100%;
  min-height: 300px;
  border: none;
  background: #fff;
  display: block;
}

/* Transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 300px;
}
</style>
