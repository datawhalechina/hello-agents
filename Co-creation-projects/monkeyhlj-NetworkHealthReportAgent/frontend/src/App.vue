<template>
  <div class="page-shell">
    <header class="hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">Network Health Report Agent</p>
        <h1>站点地图、健康报告、智能问答一屏联动</h1>
        <p class="hero-text">基于 HelloAgents + FastAPI + MCP 构建的多站点网络健康演示，支持周报生成、文件下载和全局问答。</p>
      </div>

      <div class="hero-status" v-if="runtime">
        <span class="runtime-pill" :class="runtime.qa_agent?.llm_enabled ? 'on' : 'off'">
          LLM {{ runtime.qa_agent?.llm_enabled ? 'ON' : 'OFF' }}
        </span>
        <span class="runtime-pill" :class="runtime.qa_agent?.mcp_enabled ? 'on' : 'off'">
          MCP {{ runtime.qa_agent?.mcp_enabled ? 'ON' : 'OFF' }}
        </span>
        <span class="runtime-desc">
          {{ runtime.qa_agent?.mcp_enabled ? 'MCP 工具由 Agent 通过 server_command 自动拉起' : '当前环境未启用 MCPTool，采用上下文问答回退模式' }}
        </span>
      </div>
    </header>

    <div class="toolbar panel-surface">
      <div class="field">
        <label>当前站点</label>
        <input :value="selectedSite ? selectedSite.site_name : '未选择'" disabled />
      </div>

      <div class="field">
        <label>开始日期</label>
        <input type="date" v-model="startDate" />
      </div>

      <div class="field">
        <label>结束日期</label>
        <input type="date" v-model="endDate" />
      </div>

      <button class="primary-button" @click="reloadReport" :disabled="!selectedSite || loading">
        {{ loading ? '加载中...' : '刷新报告' }}
      </button>
    </div>

    <div v-if="reportError" class="error-banner panel-surface">报告请求失败：{{ reportError }}</div>

    <main class="layout-grid">
      <section class="left-column">
        <div class="panel-surface map-panel">
          <div class="section-header">
            <div>
              <strong>站点地理分布</strong>
              <small>点击站点查看健康报告</small>
            </div>
            <span class="section-hint">地图在左，报告在下</span>
          </div>
          <SiteMap :sites="sites" :selected-site-id="selectedSite?.site_id || ''" @select="handleSelectSite" />
          <div class="site-list">
            <button
              v-for="site in sites"
              :key="site.site_id"
              class="site-chip"
              :class="{ active: site.site_id === selectedSite?.site_id }"
              @click="handleSelectSite(site)"
            >
              {{ site.city }} · {{ site.site_name }}
            </button>
          </div>
        </div>

        <ReportPanel :title="panelTitle" :report="report" />
      </section>

      <aside class="panel-surface qa-panel">
        <div class="section-header">
          <div>
            <strong>全局网络问答</strong>
            <small>示例：有几个 site？上海有哪些 site？帮我生成当前站点近一周报告</small>
          </div>
        </div>

        <div class="qa-body">
          <div class="qa-input-row">
            <input
              v-model="question"
              type="text"
              class="qa-input"
              placeholder="请输入问题，例如：帮我生成当前站点近一周的报告"
              @keyup.enter="ask"
            />
            <button class="primary-button" @click="ask" :disabled="!question.trim() || qaLoading">
              {{ qaLoading ? '回答中...' : '提问' }}
            </button>
          </div>

          <div class="qa-answer" v-if="qaAnswer">
            <h3>Agent 回答</h3>
            <pre>{{ qaAnswer }}</pre>
          </div>

          <div v-if="qaArtifact" class="qa-artifact">
            <div class="artifact-title">已生成文件</div>
            <a :href="qaArtifact.downloadUrl" target="_blank" rel="noreferrer" download>
              下载 {{ qaArtifact.fileName }}
            </a>
          </div>

          <div v-if="qaError" class="error-banner">问答失败：{{ qaError }}</div>

          <div class="qa-debug" v-if="qaDebug">
            调试信息：LLM={{ qaDebug.llmEnabled ? 'ON' : 'OFF' }}, MCP={{ qaDebug.mcpEnabled ? 'ON' : 'OFF' }}
            <span v-if="qaDebug.reportIntent">，已触发报告生成</span>
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { askQuestionStream, fetchReport, fetchRuntime, fetchSites } from './api'
import SiteMap from './components/SiteMap.vue'
import ReportPanel from './components/ReportPanel.vue'

const sites = ref([])
const selectedSite = ref(null)
const report = ref(null)
const loading = ref(false)
const runtime = ref(null)
const qaLoading = ref(false)
const question = ref('')
const qaAnswer = ref('')
const qaArtifact = ref(null)
const reportError = ref('')
const qaError = ref('')
const qaDebug = ref(null)

const today = new Date()
const endDate = ref(today.toISOString().slice(0, 10))
const startDateObj = new Date(today)
startDateObj.setDate(today.getDate() - 6)
const startDate = ref(startDateObj.toISOString().slice(0, 10))

const panelTitle = computed(() => {
  if (!selectedSite.value) {
    return '网络健康报告'
  }
  return `${selectedSite.value.site_name} - ${startDate.value} 至 ${endDate.value}`
})

async function loadSites() {
  try {
    sites.value = await fetchSites()
    runtime.value = await fetchRuntime()
    if (sites.value.length > 0) {
      await handleSelectSite(sites.value[0])
    }
  } catch (err) {
    reportError.value = err?.message || '初始化失败，请检查后端服务是否启动。'
  }
}

async function handleSelectSite(site) {
  selectedSite.value = site
  await reloadReport()
}

async function reloadReport() {
  if (!selectedSite.value) return
  loading.value = true
  reportError.value = ''
  try {
    report.value = await fetchReport(selectedSite.value.site_id, startDate.value, endDate.value)
  } catch (err) {
    report.value = null
    reportError.value = err?.message || '报告加载失败'
  } finally {
    loading.value = false
  }
}

async function ask() {
  if (!question.value.trim()) return
  qaLoading.value = true
  qaAnswer.value = ''
  qaArtifact.value = null
  qaError.value = ''
  qaDebug.value = null
  try {
    const meta = await askQuestionStream(
      question.value.trim(),
      startDate.value,
      endDate.value,
      selectedSite.value?.site_id || null,
      (chunk, streamMeta) => {
        qaAnswer.value += chunk
        qaDebug.value = streamMeta
      }
    )
    qaDebug.value = meta
    if (meta.artifactUrl) {
      qaArtifact.value = {
        fileName: meta.artifactName || 'report.md',
        downloadUrl: meta.artifactUrl
      }
    }
    if (!qaAnswer.value.trim()) {
      qaError.value = '接口已返回，但内容为空。请检查 LLM 配置或查看后端日志。'
    }
  } catch (err) {
    qaError.value = err?.message || '问答失败'
  } finally {
    qaLoading.value = false
  }
}

onMounted(loadSites)
</script>

<style scoped>
:global(body) {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 164, 0.12), transparent 28%),
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 24%),
    linear-gradient(180deg, #eef6f7 0%, #f7fafc 38%, #edf2f7 100%);
  color: #0f172a;
}

:global(*) {
  box-sizing: border-box;
}

.page-shell {
  min-height: 100vh;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-panel,
.panel-surface {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
}

.hero-panel {
  padding: 28px 30px;
  color: #eff6ff;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(15, 118, 110, 0.94) 58%, rgba(14, 165, 164, 0.9));
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-end;
}

.hero-copy {
  max-width: 860px;
}

.eyebrow {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  color: rgba(226, 232, 240, 0.8);
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 46px);
  line-height: 1.08;
}

.hero-text {
  margin: 12px 0 0;
  max-width: 72ch;
  color: rgba(226, 232, 240, 0.88);
  line-height: 1.7;
}

.hero-status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.runtime-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.1);
}

.runtime-pill.on {
  color: #dcfce7;
}

.runtime-pill.off {
  color: #fecaca;
}

.runtime-desc {
  max-width: 320px;
  color: rgba(226, 232, 240, 0.84);
  font-size: 13px;
  line-height: 1.6;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) repeat(2, minmax(0, 1fr)) auto;
  gap: 14px;
  padding: 18px;
  align-items: end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #475569;
  font-weight: 700;
}

.field input,
.qa-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  color: #0f172a;
  padding: 14px 16px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.field input:focus,
.qa-input:focus {
  border-color: rgba(20, 184, 166, 0.55);
  box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.12);
}

.primary-button,
.site-chip {
  border: none;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.primary-button {
  padding: 14px 18px;
  border-radius: 16px;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.24);
}

.primary-button:hover:not(:disabled),
.site-chip:hover:not(:disabled) {
  transform: translateY(-1px);
}

.primary-button:disabled,
.site-chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.error-banner {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(254, 226, 226, 0.9);
  color: #991b1b;
  border: 1px solid rgba(248, 113, 113, 0.18);
}

.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(340px, 0.92fr);
  gap: 20px;
  align-items: start;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.map-panel,
.qa-panel {
  padding: 20px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.section-header strong {
  display: block;
  font-size: 18px;
  color: #0f172a;
}

.section-header small,
.section-hint {
  color: #64748b;
}

.section-hint {
  white-space: nowrap;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
}

.site-list {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.site-chip {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.site-chip.active {
  color: #ecfeff;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.26);
}

.qa-panel {
  position: sticky;
  top: 18px;
}

.qa-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.qa-input-row {
  display: flex;
  gap: 12px;
}

.qa-answer {
  border-radius: 20px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.03), rgba(15, 23, 42, 0.015));
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.qa-answer h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #0f172a;
}

.qa-answer pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  color: #1e293b;
  font-family: inherit;
  font-size: 14px;
}

.qa-artifact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(236, 253, 245, 0.95);
  border: 1px solid rgba(16, 185, 129, 0.18);
}

.artifact-title {
  font-size: 13px;
  font-weight: 700;
  color: #065f46;
}

.qa-artifact a {
  color: #0f766e;
  font-weight: 700;
  text-decoration: none;
}

.qa-artifact a:hover {
  text-decoration: underline;
}

.qa-debug {
  font-size: 12px;
  color: #64748b;
  padding: 4px 2px 0;
}

@media (max-width: 1160px) {
  .toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .layout-grid {
    grid-template-columns: 1fr;
  }

  .qa-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .page-shell {
    padding: 14px;
  }

  .hero-panel,
  .map-panel,
  .qa-panel,
  .panel-surface,
  .toolbar {
    border-radius: 18px;
  }

  .hero-panel {
    padding: 20px;
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar,
  .qa-input-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .section-header {
    flex-direction: column;
  }

  .qa-artifact {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
