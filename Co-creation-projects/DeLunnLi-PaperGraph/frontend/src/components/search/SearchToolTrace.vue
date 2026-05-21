<script setup lang="ts">
export interface SearchToolCall {
  name: string
  status: 'running' | 'success' | 'error'
  params?: Record<string, unknown>
  result_summary?: string
}
defineProps<{
  toolCalls: SearchToolCall[]
}>()
</script>

<template>
  <a-collapse v-if="toolCalls.length > 0" ghost class="trace-collapse">
    <a-collapse-panel key="trace" header="中间过程（调用路径）">
      <div class="tool-calls">
        <div
          v-for="(tool, ti) in toolCalls"
          :key="ti + '-' + tool.name"
          class="tool-call"
          :class="tool.status"
        >
          <span class="tool-icon">{{
            tool.status === 'success' ? '✓' : tool.status === 'error' ? '✗' : '⟳'
          }}</span>
          <span class="tool-name">{{ tool.name }}</span>
          <span v-if="tool.result_summary" class="tool-result">{{ tool.result_summary }}</span>
        </div>
      </div>
    </a-collapse-panel>
  </a-collapse>
</template>

<style scoped>
.trace-collapse {
  margin-bottom: 12px;
}
.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tool-call {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 13px;
}
.tool-call.success {
  background: #dcfce7;
}
.tool-call.error {
  background: #fee2e2;
}
.tool-icon {
  font-size: 14px;
}
.tool-name {
  font-weight: 500;
  color: #475569;
}
.tool-result {
  color: #64748b;
  font-size: 12px;
}
</style>
