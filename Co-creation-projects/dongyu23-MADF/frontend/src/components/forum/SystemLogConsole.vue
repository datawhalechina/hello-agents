<template>
  <div class="console-window" ref="consoleRef">
    <div v-if="logs.length === 0" class="empty-log">暂无系统日志...</div>
    <div v-for="(log, index) in logs" :key="index" :class="['log-line', log.level]">
      <span class="time">[{{ formatTime(log.timestamp) }}]</span>
      <span class="source" v-if="log.source">[{{ log.source }}]</span>
      
      <!-- Speech Content -->
      <div v-if="log.level === 'speech'" class="log-content speech">
        {{ log.content }}
      </div>
      
      <!-- Thought Content (JSON) -->
      <div v-else-if="log.level === 'thought'" class="log-content thought">
        <pre>{{ formatJson(log.content) }}</pre>
      </div>
      
      <!-- Regular Log -->
      <span v-else class="msg">{{ log.content }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useForumStore } from '@/stores/forum'
import { useRoute } from 'vue-router'

const store = useForumStore()
const route = useRoute()
const logs = computed(() => store.systemLogs)
const consoleRef = ref<HTMLElement | null>(null)

const forumId = Number(route.params.id)

onMounted(() => {
    if (forumId) {
        store.fetchSystemLogs(forumId)
    }
})

const formatTime = (isoString: string) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  // Use 'en-GB' locale for 24-hour format (HH:MM:SS) which is standard for logs
  // And ensure we render local time correctly
  return date.toLocaleTimeString('en-GB', { hour12: false }) + '.' + date.getMilliseconds().toString().padStart(3, '0')
}

const formatJson = (jsonStr: string) => {
    try {
        const obj = JSON.parse(jsonStr)
        return JSON.stringify(obj, null, 2)
    } catch (e) {
        return jsonStr
    }
}

// Auto scroll to bottom
watch(logs, () => {
  nextTick(() => {
    if (consoleRef.value) {
      consoleRef.value.scrollTop = consoleRef.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<style scoped>
.console-window {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  padding: 12px;
  height: 400px;
  overflow-y: auto;
  border-radius: 4px;
  border: 1px solid #333;
  font-size: 13px;
  line-height: 1.5;
}

.log-line {
  margin-bottom: 8px;
  word-break: break-all;
  border-bottom: 1px solid #2a2a2a;
  padding-bottom: 4px;
}

.time {
  color: #808080;
  margin-right: 8px;
  font-size: 12px;
}

.source {
  color: #569cd6;
  margin-right: 8px;
  font-weight: bold;
}

.info .msg { color: #4ec9b0; }
.warning .msg { color: #ce9178; }
.error .msg { color: #f44747; }

.log-content {
    margin-top: 4px;
    padding-left: 20px;
}

.speech {
    color: #dcdcaa;
    white-space: pre-wrap;
}

.thought {
    color: #9cdcfe;
}

.thought pre {
    margin: 0;
    font-family: inherit;
    white-space: pre-wrap;
}

.empty-log {
  color: #666;
  text-align: center;
  margin-top: 20px;
}

/* Scrollbar styling */
.console-window::-webkit-scrollbar {
  width: 8px;
}
.console-window::-webkit-scrollbar-track {
  background: #1e1e1e;
}
.console-window::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 4px;
}
.console-window::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}
</style>