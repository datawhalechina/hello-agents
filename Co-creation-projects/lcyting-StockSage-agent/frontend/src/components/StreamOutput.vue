<template>
  <div class="stream-output">
    <div v-if="isStreaming" class="streaming-bar">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ statusText || '正在分析...' }}</span>
    </div>

    <div v-if="metaInfo" class="meta-info">
      <el-tag size="small" type="info">{{ metaInfo.stock_code }}</el-tag>
      <span v-if="metaInfo.stock_name" class="stock-name">{{ metaInfo.stock_name }}</span>
    </div>

    <div v-if="emotionalText" class="emotional-block">
      {{ emotionalText }}
    </div>

    <div v-if="renderedContent" class="content-block markdown-body" v-html="renderedContent"></div>

    <el-empty v-if="!isStreaming && !renderedContent && !error" description="点击上方按钮开始分析" :image-size="60" />

    <div v-if="error" class="error-block">
      <el-alert :title="error" type="error" :closable="false" show-icon />
    </div>

    <div v-if="!isStreaming && renderedContent" class="action-bar">
      <el-button size="small" @click="$emit('save')" :disabled="!renderedContent">
        <el-icon><FolderChecked /></el-icon> 保存历史
      </el-button>
      <el-button size="small" @click="$emit('download')" :disabled="!renderedContent">
        <el-icon><Download /></el-icon> 下载报告
      </el-button>
      <el-button size="small" @click="$emit('clear')">
        <el-icon><Delete /></el-icon> 清除
      </el-button>
    </div>
  </div>
</template>

<script>
export default { name: 'StreamOutput' }
</script>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  content: { type: String, default: '' },
  statusText: { type: String, default: '' },
  emotionalText: { type: String, default: '' },
  metaInfo: { type: Object, default: null },
  isStreaming: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['save', 'download', 'clear'])

function simpleMarkdown(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/^- (.*$)/gim, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
  html = html.replace(/\n\n/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')
  html = '<p>' + html + '</p>'
  return html
}

const renderedContent = computed(() => {
  return simpleMarkdown(props.content)
})
</script>

<style scoped>
.stream-output {
  min-height: 200px;
  position: relative;
}

.streaming-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #ecf5ff;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #409eff;
}

.meta-info {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.emotional-block {
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #67c23a;
  line-height: 1.6;
}

.content-block {
  margin-bottom: 12px;
  line-height: 1.8;
  font-size: 14px;
}

.content-block :deep(h2) { font-size: 16px; margin: 16px 0 8px; }
.content-block :deep(h3) { font-size: 14px; margin: 12px 0 6px; }
.content-block :deep(p) { margin: 6px 0; }
.content-block :deep(ul), .content-block :deep(ol) { padding-left: 20px; }
.content-block :deep(li) { margin: 4px 0; }
.content-block :deep(code) {
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
.content-block :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.error-block {
  margin-bottom: 12px;
}

.action-bar {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
</style>
