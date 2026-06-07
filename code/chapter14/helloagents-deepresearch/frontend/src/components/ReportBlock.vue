<template>
  <div class="report-block" :class="{ 'block-highlight': reportHighlight }">
    <div class="block-header">
      <h3>找实习行动报告</h3>
      <button
        type="button"
        class="secondary-btn compact-btn"
        :disabled="!reportMarkdown"
        @click="emit('copy-report')"
      >
        复制报告
      </button>
    </div>
    <pre class="block-pre">{{ reportMarkdown }}</pre>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  reportHighlight: boolean;
  reportMarkdown: string;
}>();

const emit = defineEmits<{
  "copy-report": [];
}>();
</script>

<style scoped>
.report-block {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-block h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.report-block .block-header h3 {
  margin: 0;
}
</style>
