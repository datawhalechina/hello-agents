<template>
  <div class="code-editor" :class="{ 'exercise-mode': exerciseData !== null }">
    <div class="editor-header">
      <div class="tabs">
        <select v-model="selectedLanguage" class="lang-select" @change="onLanguageChange" :disabled="exerciseData !== null">
          <option v-for="lang in languages" :key="lang.id" :value="lang.id">
            {{ lang.label }}
          </option>
        </select>
        <span v-if="exerciseData" class="exercise-indicator">📝 练习模式</span>
        <span v-else class="tab active">{{ currentTab }}</span>
      </div>
      <div class="header-actions">
        <button class="submit-btn" @click="submitForReview" :disabled="submitting">
          {{ submitting ? (exerciseData ? '提交中...' : langStore.t('codeEditor.submitting')) : (exerciseData ? '📝 提交练习反馈' : langStore.t('codeEditor.submitFeedback')) }}
        </button>
        <button class="run-btn" @click="runCode" :disabled="running">
          <span v-if="!running">{{ currentExecutor === 'iframe' ? 'Preview' : langStore.t('codeEditor.run') }}</span>
          <span v-else>{{ currentExecutor === 'iframe' ? 'Loading...' : langStore.t('codeEditor.running') }}</span>
        </button>
        <button v-if="exerciseData" class="close-exercise-btn" @click="closeExercise">✕</button>
      </div>
    </div>
    
    <div class="editor-container" ref="editorContainer" @mousedown="focusEditor"></div>
    
    <div class="output-panel" :class="{ 'iframe-mode': currentExecutor === 'iframe' }">
      <div class="output-header">
        <span class="output-title">{{ hasError ? langStore.t('codeEditor.error') : (currentExecutor === 'iframe' ? 'Preview' : langStore.t('codeEditor.output')) }}</span>
        <button class="clear-btn" @click="clearOutput" v-if="output || error || previewSrc">{{ langStore.t('codeEditor.clear') }}</button>
      </div>

      <!-- iframe preview for HTML/CSS -->
      <div v-if="previewSrc" class="output-content preview-content">
        <iframe :srcdoc="previewSrc" sandbox="allow-scripts" class="preview-iframe" />
      </div>

      <!-- normal output panel -->
      <div v-else class="output-content">
        <pre v-if="output" class="output-text">{{ output }}</pre>
        <pre v-if="error" class="error-text">{{ error }}</pre>
        <div v-if="!output && !error && !feedback" class="output-placeholder">
          {{ currentExecutor === 'iframe' ? 'Click "Preview" to render your code.' : langStore.t('codeEditor.placeholder') }}
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
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import loader from '@monaco-editor/loader'
import { useLangStore } from '../stores/langStore'
import { useAuthStore } from '../stores/authStore'

// ── Types ──────────────────────────────────────────────────────────────

interface LangConfig {
  id: string
  label: string
  monaco: string
  tab: string
  executor: 'backend' | 'iframe'
  defaultCode: string
}

// ── Language definitions ───────────────────────────────────────────────

const languages: LangConfig[] = [
  {
    id: 'python',
    label: 'Python',
    monaco: 'python',
    tab: 'main.py',
    executor: 'backend',
    defaultCode: '# Write Python code here\nprint("Hello World!")',
  },
  {
    id: 'javascript',
    label: 'JavaScript',
    monaco: 'javascript',
    tab: 'script.js',
    executor: 'backend',
    defaultCode: '// Write JavaScript code here\nconsole.log("Hello World!");',
  },
  {
    id: 'typescript',
    label: 'TypeScript',
    monaco: 'typescript',
    tab: 'index.ts',
    executor: 'backend',
    defaultCode:
      '// Write TypeScript code here\nconst msg: string = "Hello World!";\nconsole.log(msg);',
  },
  {
    id: 'html',
    label: 'HTML',
    monaco: 'html',
    tab: 'index.html',
    executor: 'iframe',
    defaultCode:
      '<!DOCTYPE html>\n<html>\n<head>\n  <title>My Page</title>\n  <style>\n    body { font-family: sans-serif; padding: 20px; }\n  </style>\n</head>\n<body>\n  <h1>Hello World!</h1>\n  <p>Write your HTML here.</p>\n</body>\n</html>',
  },
  {
    id: 'css',
    label: 'CSS',
    monaco: 'css',
    tab: 'style.css',
    executor: 'iframe',
    defaultCode:
      '/* Write CSS code here */\nbody {\n  font-family: sans-serif;\n  background: #f0f0f0;\n  margin: 20px;\n}',
  },
  {
    id: 'bash',
    label: 'Bash',
    monaco: 'shell',
    tab: 'script.sh',
    executor: 'backend',
    defaultCode: '# Write shell commands here\necho "Hello World!"',
  },
]

// ── Emits ─────────────────────────────────────────────────────────────

const emit = defineEmits<{
  exerciseSubmitted: [result: { feedback: string }]
}>()

// ── Props ──────────────────────────────────────────────────────────────

const props = withDefaults(defineProps<{
  exerciseData?: { code: string; language: string; lessonId?: string | null } | null
}>(), {
  exerciseData: null,
})

// ── State ──────────────────────────────────────────────────────────────

const editorContainer = ref<HTMLElement>()
const output = ref('')
const error = ref('')
const previewSrc = ref('')
const running = ref(false)
const submitting = ref(false)
const feedback = ref('')
const feedbackError = ref('')
const selectedLanguage = ref('python')
const langStore = useLangStore()
const authStore = useAuthStore()

let editor: any = null
let monaco: any = null

// ── Computed ───────────────────────────────────────────────────────────

const currentLangConfig = computed((): LangConfig => {
  return languages.find((l) => l.id === selectedLanguage.value) || languages[0]
})

const currentTab = computed(() => currentLangConfig.value.tab)
const currentExecutor = computed(() => currentLangConfig.value.executor)
const hasError = computed(() => !!error.value)

// ── Lifecycle ──────────────────────────────────────────────────────────

onMounted(async () => {
  monaco = await loader.init()

  editor = monaco.editor.create(editorContainer.value!, {
    value: currentLangConfig.value.defaultCode,
    language: currentLangConfig.value.monaco,
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

  // Ctrl+Enter execute
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    runCode()
  })

  // 自动聚焦编辑器，否则空格键等键盘输入不会生效
  editor.focus()
})

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
  }
})

// ── Language switching ─────────────────────────────────────────────────

function onLanguageChange() {
  const cfg = currentLangConfig.value

  if (editor && monaco) {
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, cfg.monaco)
    }
    editor.setValue(cfg.defaultCode)
  }

  clearOutput()
}

// ── Exercise mode ──────────────────────────────────────────────────────

watch(() => props.exerciseData, (data) => {
  if (data && editor && monaco) {
    // Switch to exercise language
    const lang = languages.find(l => l.id === data.language)
    if (lang) {
      selectedLanguage.value = lang.id
      const model = editor.getModel()
      if (model) {
        monaco.editor.setModelLanguage(model, lang.monaco)
      }
    }
    editor.setValue(data.code)
    editor.focus()
    clearOutput()
  }
}, { immediate: true })

function focusEditor() {
  if (editor) {
    editor.focus()
  }
}

function closeExercise() {
  // Restore default code for current language
  const cfg = currentLangConfig.value
  if (editor) {
    editor.setValue(cfg.defaultCode)
  }
  clearOutput()
}

// ── Run / Preview ──────────────────────────────────────────────────────

const runCode = async () => {
  if (running.value || !editor) return

  const code = editor.getValue()
  if (!code.trim()) return

  running.value = true
  output.value = ''
  error.value = ''
  feedback.value = ''
  feedbackError.value = ''
  previewSrc.value = ''

  try {
    if (currentExecutor.value === 'iframe') {
      // HTML: render directly; CSS: wrap in a minimal HTML shell
      if (selectedLanguage.value === 'css') {
        previewSrc.value =
          "<html><head><style>" + code + "</style></head><body><div class='preview-content'>Preview your styles here</div></body></html>"
      } else {
        previewSrc.value = code
      }
    } else {
      const response = await axios.post('/api/code/execute', {
        code: code,
        language: selectedLanguage.value,
      })

      const result = response.data
      output.value = result.output
      error.value = result.error
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || '请求失败'
  } finally {
    running.value = false
  }
}

// ── Submit for review ──────────────────────────────────────────────────

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
      language: selectedLanguage.value,
      output: output.value,
      error: error.value,
      success: !error.value,
      exit_code: error.value ? 1 : 0,
      user_id: authStore.userId || 'default',
      lesson_id: props.exerciseData?.lessonId || null,
    })

    feedback.value = response.data.feedback
    // 通知父组件练习已提交
    emit('exerciseSubmitted', { feedback: response.data.feedback })
  } catch (err: any) {
    feedbackError.value =
      err.response?.data?.detail || langStore.t('codeEditor.feedbackError')
  } finally {
    submitting.value = false
  }
}

// ── Utilities ──────────────────────────────────────────────────────────

const clearOutput = () => {
  output.value = ''
  error.value = ''
  previewSrc.value = ''
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
  border-radius: 8px 8px 0 0;
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tabs {
  display: flex;
  gap: 8px;
  align-items: center;
}

.lang-select {
  background: #3c3c3c;
  color: #fff;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

.lang-select:hover {
  background: #4a4a4a;
}

.lang-select option {
  background: #3c3c3c;
  color: #fff;
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

.exercise-indicator {
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  background: #667eea;
  border-radius: 4px;
  margin-left: 8px;
}

.close-exercise-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #969696;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-exercise-btn:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}

.exercise-mode .editor-header {
  border-bottom-color: #667eea;
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

.output-panel.iframe-mode {
  max-height: none;
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

.preview-content {
  max-height: none;
  overflow: visible;
}

.preview-iframe {
  width: 100%;
  min-height: 300px;
  border: none;
  background: #fff;
  border-radius: 4px;
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
