<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { renderMarkdown } from '../markdown'

const symbol = ref('BTC')
const record = ref(false)
const busy = ref(false)
const reports = ref([])
const markdown = ref('')
const metrics = ref(null)
const error = ref('')

async function loadReports() {
  reports.value = await api('/reports')
}

async function openReport(filename) {
  const data = await api(`/reports/${encodeURIComponent(filename)}`)
  markdown.value = `${data.report || ''}\n\n${data.appendix || ''}`
  metrics.value = null
}

async function analyze() {
  busy.value = true
  error.value = ''
  try {
    const data = await api('/analyze', {
      method: 'POST',
      body: JSON.stringify({ symbol: symbol.value, record: record.value }),
    })
    markdown.value = data.report || ''
    metrics.value = data
    await loadReports()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await loadReports()
  if (reports.value[0]) openReport(reports.value[0].filename)
})
</script>

<template>
  <div class="page reports-page">
    <header class="page-head">
      <h2>研报工作台</h2>
      <p>三位分析师并行，协调员汇总为条件化建议</p>
    </header>
    <div class="split">
      <aside class="rail">
        <form class="panel form" @submit.prevent="analyze">
          <label>分析标的</label>
          <div class="row">
            <input v-model="symbol" maxlength="12" />
            <button class="primary" :disabled="busy">{{ busy ? '分析中…' : '开始分析' }}</button>
          </div>
          <div class="chips">
            <button v-for="item in ['BTC', 'ETH', 'SOL', 'BNB']" :key="item" type="button" class="ghost" @click="symbol = item">{{ item }}</button>
          </div>
          <label class="check"><input type="checkbox" v-model="record" /> 通过门禁后归档信号</label>
        </form>
        <section class="panel">
          <div v-for="item in reports" :key="item.filename" class="list-item" @click="openReport(item.filename)">
            <div>
              <strong>{{ item.symbol }}</strong>
              <div class="muted">{{ item.stamp }} · {{ item.passed ? '通过' : '未通过' }}</div>
            </div>
          </div>
        </section>
      </aside>
      <article class="panel report">
        <p v-if="error" class="error">{{ error }}</p>
        <div v-if="metrics" class="metrics">
          <span>门禁 {{ metrics.gate_passed ? '通过' : '未通过' }}</span>
          <span>耗时 {{ Number(metrics.metrics?.elapsed_seconds || 0).toFixed(1) }}s</span>
        </div>
        <div class="md" v-html="renderMarkdown(markdown || '选择币种后开始分析。')" />
      </article>
    </div>
  </div>
</template>

<style scoped>
.reports-page { min-height: 0; }
.split { flex: 1; display: flex; gap: 16px; min-height: 0; }
.rail { width: 300px; display: flex; flex-direction: column; gap: 12px; overflow: auto; }
.form { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; gap: 8px; }
.row input {
  flex: 1;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 8px 10px;
}
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.check { color: var(--muted); font-size: 13px; display: flex; gap: 8px; align-items: center; }
.report { flex: 1; overflow: auto; padding: 20px; }
.metrics { display: flex; gap: 16px; color: var(--muted); margin-bottom: 12px; }
.error { color: var(--bad); }
</style>
