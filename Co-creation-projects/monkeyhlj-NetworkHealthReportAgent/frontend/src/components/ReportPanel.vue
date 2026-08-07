<template>
  <div class="panel">
    <div class="report-header">
      <div>
        <strong>{{ title }}</strong>
      </div>
      <span v-if="report" class="badge" :class="report.health_level">{{ report.health_level }}</span>
    </div>

    <div v-if="!report" class="empty">请选择一个站点查看健康报告</div>

    <div v-else class="report-body">
      <div class="kpis">
        <div class="kpi">
          <div class="label">健康评分</div>
          <div class="value">{{ report.health_score }}</div>
        </div>
        <div class="kpi">
          <div class="label">设备在线率</div>
          <div class="value">{{ (report.sections.device_status.online_rate * 100).toFixed(2) }}%</div>
        </div>
        <div class="kpi">
          <div class="label">终端合规率</div>
          <div class="value">{{ (report.sections.user_status.compliant_rate * 100).toFixed(2) }}%</div>
        </div>
      </div>

      <div class="section">
        <h3>日志分析 Agent</h3>
        <p>{{ report.sections.log_analysis.summary }}</p>
      </div>

      <div class="section">
        <h3>设备状态 Agent</h3>
        <p>{{ report.sections.device_status.summary }}</p>
      </div>

      <div class="section">
        <h3>用户状态 Agent</h3>
        <p>{{ report.sections.user_status.summary }}</p>
      </div>

      <div class="section">
        <h3>网络健康报告 Agent 建议</h3>
        <ul class="recommendation-list">
          <li v-for="(item, idx) in report.recommendations" :key="idx">{{ item }}</li>
        </ul>
      </div>

      <div class="section" v-if="report.llm_insight">
        <h3>大模型综合研判</h3>
        <p>{{ report.llm_insight }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'ReportPanel' })

defineProps({
  title: {
    type: String,
    default: '网络健康报告'
  },
  report: {
    type: Object,
    default: null
  }
})
</script>
