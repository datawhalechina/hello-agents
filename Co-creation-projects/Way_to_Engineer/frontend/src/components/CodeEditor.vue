<template>
  <div class="code-editor">
    <div class="editor-header">
      <div class="tabs">
        <span class="tab active">main.py</span>
      </div>
      <div class="header-actions">
        <button class="submit-btn" @click="submitForReview" :disabled="submitting">
          {{ submitting ? langStore.t('codeEditor.submitting') : langStore.t('codeEditor.submitFeedback') }}
        </button>
        <button class="run-btn" @click="runCode" :disabled="running">
          <span v-if="!running">{{ langStore.t('codeEditor.run') }}</span>
          <span v-else>{{ langStore.t('codeEditor.running') }}</span>
        </button>
      </div>
    </div>
    
    <div class="editor-container" ref="editorContainer"></div>
    
    <div class="output-panel">
      <div class="output-header">
        <span class="output-title">{{ hasError ? langStore.t('codeEditor.error') : langStore.t('codeEditor.output') }}</span>
        <button class="clear-btn" @click="clearOutput" v-if="output || error">{{ langStore.t('codeEditor.clear') }}</button>
      </div>
      <div class="output-content">
        <pre v-if="output" class="output-text">{{ output }}</pre>
        <pre v-if="error" class="error-text">{{ error }}</pre>
        <div v-if="!output && !error && !feedback" class="output-placeholder">
          {{ langStore.t('codeEditor.placeholder') }}
        </div>
      </div>
      
      <div v-if="feedback" class="feedback-section">
        <div class="feedback-header">
          <span class="feedback-title">{{ langStore.t('codeEditor.feedbackTitle') }}</span>
        </div>
        <div class="feedback-body">
          <pre class="feedback-text">{{ feedback }}</pre>
        </div>
      </div>
      <div v-if="feedbackError" class="feedback-section feedback-error">
        <div class="feedback-body">
          <pre class="feedback-text error-text">{{ feedbackError }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import axios from 'axios'
import loader from '@monaco-editor/loader'
import { useLangStore } from '../stores/langStore'
import { useAuthStore } from '../stores/authStore'

const editorContainer = ref<HTMLElement>()
const output = ref('')
const error = ref('')
const running = ref(false)
const submitting = ref(false)
const feedback = ref('')
const feedbackError = ref('')
const langStore = useLangStore()
const authStore = useAuthStore()

let editor: any = null
let monaco: any = null

const hasError = computed(() => !!error.value)

const defaultCode = computed(() => langStore.t('codeEditor.defaultCode'))

onMounted(async () => {
  // 加载Monaco Editor
  monaco = await loader.init()
  
  // 创建编辑器
  editor = monaco.editor.create(editorContainer.value!, {
    value: defaultCode.value,
    language: 'python',
    theme: 'vs-dark',
    automaticLayout: true,
    fontSize: 14,
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    roundedSelection: false,
    readOnly: false,
    cursorStyle: 'line',
    padding: { top: 12, bottom: 12 },
    suggest: {
      showKeywords: true,
      showSnippets: true,
    },
    tabSize: 4,
    insertSpaces: true,
  })
  
  // Ctrl+Enter 执行代码
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    runCode()
  })
})

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
  }
})

const runCode = async () => {
  if (running.value || !editor) return
  
  const code = editor.getValue()
  if (!code.trim()) return
  
  running.value = true
  output.value = ''
  error.value = ''
  feedback.value = ''
  feedbackError.value = ''
  
  try {
    const response = await axios.post('/api/code/execute', {
      code: code,
      language: 'python',
    })
    
    const result = response.data
    output.value = result.output
    error.value = result.error
  } catch (err: any) {
    error.value = err.response?.data?.detail || '请求失败'
  } finally {
    running.value = false
  }
}

const submitForReview = async () => {
  if (submitting.value || !editor) return
  
  const code = editor.getValue()
  if (!code.trim()) return
  
  submitting.value = true
  feedback.value = ''
  feedbackError.value = ''
  
  try {
    const response = await axios.post('/api/code/submit', {
      code: code,
      language: 'python',
      output: output.value,
      error: error.value,
      success: !error.value,
      exit_code: error.value ? 1 : 0,
      user_id: authStore.userId || 'default',
    })
    
    feedback.value = response.data.feedback
  } catch (err: any) {
    feedbackError.value = err.response?.data?.detail || langStore.t('codeEditor.feedbackError')
  } finally {
    submitting.value = false
  }
}

const clearOutput = () => {
  output.value = ''
  error.value = ''
  feedback.value = ''
  feedbackError.value = ''
}
</script>

<style scoped>
.code-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #3c3c3c;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  height: 40px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tabs {
  display: flex;
  gap: 2px;
}

.tab {
  padding: 8px 16px;
  font-size: 13px;
  color: #969696;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab.active {
  color: #fff;
  border-bottom-color: #007acc;
  background: #1e1e1e;
}

.run-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: #0e639c;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.run-btn:hover:not(:disabled) {
  background: #1177bb;
}

.run-btn:disabled {
  background: #3c3c3c;
  color: #6c6c6c;
  cursor: not-allowed;
}

.submit-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: #2d7d46;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.submit-btn:hover:not(:disabled) {
  background: #389e54;
}

.submit-btn:disabled {
  background: #3c3c3c;
  color: #6c6c6c;
  cursor: not-allowed;
}

.editor-container {
  flex: 1;
  min-height: 300px;
}

.output-panel {
  border-top: 1px solid #3c3c3c;
  background: #1e1e1e;
  max-height: 45vh;
  overflow-y: auto;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
}

.output-title {
  font-size: 12px;
  font-weight: 500;
  color: #ccc;
  text-transform: uppercase;
}

.clear-btn {
  padding: 2px 8px;
  background: transparent;
  color: #969696;
  border: 1px solid #3c3c3c;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #3c3c3c;
  color: #fff;
}

.output-content {
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
}

.output-text, .error-text {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.output-text {
  color: #d4d4d4;
}

.error-text {
  color: #f48771;
}

.output-placeholder {
  color: #6c6c6c;
  font-size: 13px;
  font-style: italic;
}

.feedback-section {
  border-top: 1px solid #3c3c3c;
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #1a3a2a;
  border-bottom: 1px solid #3c3c3c;
}

.feedback-title {
  font-size: 12px;
  font-weight: 500;
  color: #8dd0a8;
  text-transform: uppercase;
}

.feedback-body {
  padding: 12px;
  background: #1a2a1e;
}

.feedback-text {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #cce8d0;
}

.feedback-error .feedback-body {
  background: #2a1a1a;
}

.feedback-error .feedback-text {
  color: #f48771;
}
</style>
