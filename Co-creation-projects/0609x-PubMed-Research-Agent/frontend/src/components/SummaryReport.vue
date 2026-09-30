<template>
  <div v-if="!analysis" class="no-analysis">
    <el-empty description="暂无 AI 分析结果" :image-size="80" />
  </div>

  <div v-else class="report">
    <div class="report-head">
      <span class="head-title">AI 文献总结报告</span>
      <CopyButton :text="reportMarkdown" />
    </div>

    <el-alert
      v-if="result.status === 'partial'"
      type="warning"
      :closable="false"
      show-icon
      title="部分完成：LLM 总结失败，仅展示检索结果"
      class="status-alert"
    />
    <el-alert
      v-if="result.status === 'failed'"
      type="error"
      :closable="false"
      show-icon
      :title="'检索失败：' + (result.error_message || '未知错误')"
      class="status-alert"
    />
    <el-alert
      v-else-if="result.error_message"
      type="warning"
      :closable="false"
      show-icon
      :title="result.error_message"
      class="status-alert"
    />

    <el-card shadow="never" class="section">
      <template #header><span class="section-title">🔬 研究背景</span></template>
      <div class="markdown-body" v-html="renderMarkdown(analysis.research_background)" />
    </el-card>

    <el-card shadow="never" class="section">
      <template #header><span class="section-title">🔥 当前研究热点</span></template>
      <el-empty v-if="!analysis.current_hotspots.length" description="无" :image-size="50" />
      <el-row v-else :gutter="12">
        <el-col v-for="(h, i) in analysis.current_hotspots" :key="i" :xs="24" :sm="12">
          <el-card shadow="hover" class="hotspot-card">
            <div class="hotspot-name">{{ h.topic }}</div>
            <div class="hotspot-desc">{{ h.description }}</div>
            <div class="hotspot-evidence">
              <el-tag
                v-for="pm in h.evidence"
                :key="pm"
                size="small"
                type="info"
                class="pmid-tag"
              >{{ pm }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="section">
      <template #header><span class="section-title">💡 主要发现</span></template>
      <ul v-if="analysis.main_findings.length" class="finding-list">
        <li v-for="(f, i) in analysis.main_findings" :key="i">{{ f }}</li>
      </ul>
      <el-empty v-else description="无" :image-size="50" />
    </el-card>

    <el-card shadow="never" class="section">
      <template #header><span class="section-title">🧪 实验验证方法</span></template>
      <el-empty v-if="!analysis.experimental_methods.length" description="无" :image-size="50" />
      <el-table
        v-else
        :data="analysis.experimental_methods"
        size="small"
        border
        style="width: 100%"
      >
        <el-table-column prop="method" label="方法" min-width="200" />
        <el-table-column prop="purpose" label="用途" min-width="240" />
        <el-table-column prop="frequency" label="文献数" width="90" align="center" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="section">
      <template #header><span class="section-title">🚀 未来研究方向</span></template>
      <el-empty v-if="!analysis.future_directions.length" description="无" :image-size="50" />
      <div v-else>
        <div v-for="(d, i) in analysis.future_directions" :key="i" class="direction-item">
          <div class="direction-topic">{{ i + 1 }}. {{ d.topic }}</div>
          <div class="direction-rationale">{{ d.rationale }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CopyButton from './CopyButton.vue'
import { renderMarkdown } from '@/utils/format'
import type { SearchOut } from '@/types'

const props = defineProps<{ result: SearchOut }>()

const analysis = computed(() => props.result.analysis)

const reportMarkdown = computed(() => {
  if (!analysis.value) return ''
  const a = analysis.value
  const hotspots = a.current_hotspots
    .map((h) => `- **${h.topic}**：${h.description}`)
    .join('\n')
  const findings = a.main_findings.map((f) => `- ${f}`).join('\n')
  const methods = a.experimental_methods
    .map((m) => `- **${m.method}**：${m.purpose}（${m.frequency} 篇）`)
    .join('\n')
  const directions = a.future_directions.map((d) => `- **${d.topic}**：${d.rationale}`).join('\n')

  return [
    `# AI 文献总结报告：${props.result.query_text}`,
    '',
    '## 研究背景',
    a.research_background,
    '',
    '## 当前研究热点',
    hotspots || '无',
    '',
    '## 主要发现',
    findings || '无',
    '',
    '## 实验验证方法',
    methods || '无',
    '',
    '## 未来研究方向',
    directions || '无',
    ''
  ].join('\n')
})
</script>

<style scoped>
.no-analysis {
  padding-top: 24px;
}
.report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.head-title {
  font-size: 18px;
  font-weight: 600;
}
.status-alert {
  margin-bottom: 12px;
}
.section {
  margin-bottom: 12px;
}
.section-title {
  font-size: 17px;
  font-weight: 600;
}
.markdown-body {
  color: var(--el-text-color-primary);
  font-size: 16px;
  line-height: 1.8;
}
.hotspot-card {
  margin-bottom: 12px;
}
.hotspot-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
}
.hotspot-desc {
  color: var(--el-text-color-regular);
  font-size: 15px;
  line-height: 1.8;
  margin-bottom: 8px;
}
.hotspot-evidence {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}
.finding-list {
  margin: 0;
  padding-left: 20px;
  font-size: 15px;
  line-height: 1.9;
}
.pmid-tag {
  margin-right: 6px;
}
.direction-item {
  margin-bottom: 12px;
}
.direction-topic {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.direction-rationale {
  color: var(--el-text-color-regular);
  font-size: 15px;
  line-height: 1.8;
}
:deep(.el-table) {
  font-size: 15px;
}
:deep(.el-table .cell) {
  line-height: 1.7;
  padding-top: 5px;
  padding-bottom: 5px;
}
</style>
