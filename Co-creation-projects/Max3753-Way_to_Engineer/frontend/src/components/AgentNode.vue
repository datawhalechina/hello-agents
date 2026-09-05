<template>
  <div :class="['agent-node', type, { active: status === 'active' || status === 'processing' }]" @click="$emit('node-click', type)">
    <div class="node-header">
      <span class="node-icon">{{ icon }}</span>
      <span class="node-title">{{ label }}</span>
      <span v-if="status === 'active' || status === 'processing'" class="header-pulse"></span>
    </div>
    <div class="node-body">
      <p class="node-desc">{{ description }}</p>
      <div class="node-status">
        <span class="status-dot" :class="status"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div class="node-stats">
        <span class="stat">
          <span class="stat-icon">💬</span>
          <span class="stat-value">{{ messageCount }}</span>
        </span>
        <span class="stat">
          <span class="stat-icon">🕐</span>
          <span class="stat-value">{{ lastUsedText }}</span>
        </span>
      </div>
    </div>
    <div class="node-handles">
      <div class="handle handle-left"></div>
      <div class="handle handle-right"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineEmits<{
  (e: 'node-click', type: string): void
}>()

const props = withDefaults(defineProps<{
  type: 'orchestrator' | 'tutor' | 'debug' | 'review' | 'arch' | 'coach'
  label: string
  description?: string
  status?: 'active' | 'idle' | 'error' | 'processing'
  messageCount?: number
  lastUsed?: number | null
}>(), {
  status: 'idle',
  messageCount: 0,
  lastUsed: null
})

const icon = computed(() => {
  const icons: Record<string, string> = {
    orchestrator: '🧠',
    tutor: '👨‍🏫',
    debug: '🐛',
    review: '🔍',
    arch: '🏗️',
    coach: '🎯',
  }
  return icons[props.type] || '🤖'
})

const description = computed(() => {
  const descs: Record<string, string> = {
    orchestrator: '路由和协调',
    tutor: '概念讲解答疑',
    debug: '错误分析修复',
    review: '代码质量审查',
    arch: '架构设计咨询',
    coach: '学习路径规划',
  }
  return props.description || descs[props.type] || ''
})

const statusText = computed(() => {
  const texts: Record<string, string> = {
    active: '运行中',
    processing: '处理中',
    idle: '空闲',
    error: '错误',
  }
  return texts[props.status || 'idle'] || '空闲'
})

const lastUsedText = computed(() => {
  if (!props.lastUsed) return '-'
  const diff = Date.now() - props.lastUsed
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return `${Math.floor(diff / 86400000)}d`
})
</script>

<style scoped>
.agent-node {
  min-width: 180px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  border: 2px solid transparent;
  transition: all 0.3s;
  cursor: pointer;
}

.agent-node:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.agent-node.active {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.2);
}

.agent-node.orchestrator { border-color: #667eea; }
.agent-node.orchestrator.active { box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2), 0 6px 24px rgba(102, 126, 234, 0.3); }
.agent-node.tutor { border-color: #764ba2; }
.agent-node.tutor.active { box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.2), 0 6px 24px rgba(118, 75, 162, 0.3); }
.agent-node.debug { border-color: #f5222d; }
.agent-node.debug.active { box-shadow: 0 0 0 3px rgba(245, 34, 45, 0.2), 0 6px 24px rgba(245, 34, 45, 0.3); }
.agent-node.review { border-color: #52c41a; }
.agent-node.review.active { box-shadow: 0 0 0 3px rgba(82, 196, 26, 0.2), 0 6px 24px rgba(82, 196, 26, 0.3); }
.agent-node.arch { border-color: #fa8c16; }
.agent-node.arch.active { box-shadow: 0 0 0 3px rgba(250, 140, 22, 0.2), 0 6px 24px rgba(250, 140, 22, 0.3); }
.agent-node.coach { border-color: #722ed1; }
.agent-node.coach.active { box-shadow: 0 0 0 3px rgba(114, 46, 209, 0.2), 0 6px 24px rgba(114, 46, 209, 0.3); }

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: white;
  position: relative;
  overflow: hidden;
}

.orchestrator .node-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.tutor .node-header { background: linear-gradient(135deg, #764ba2 0%, #9b59b6 100%); }
.debug .node-header { background: linear-gradient(135deg, #f5222d 0%, #cf1322 100%); }
.review .node-header { background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); }
.arch .node-header { background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%); }
.coach .node-header { background: linear-gradient(135deg, #722ed1 0%, #531dab 100%); }

.header-pulse {
  position: absolute;
  right: 12px;
  width: 10px;
  height: 10px;
  background: white;
  border-radius: 50%;
  animation: header-pulse 1.5s infinite;
}

@keyframes header-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.node-icon {
  font-size: 20px;
}

.node-title {
  font-size: 14px;
  font-weight: 600;
}

.node-body {
  padding: 12px 16px;
}

.node-desc {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #666;
}

.node-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d9d9d9;
}

.status-dot.active {
  background: #52c41a;
  animation: dot-pulse 1.5s infinite;
}

.status-dot.processing {
  background: #1890ff;
  animation: dot-pulse 1s infinite;
}

.status-dot.idle {
  background: #d9d9d9;
}

.status-dot.error {
  background: #f5222d;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.status-text {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.node-stats {
  display: flex;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #999;
}

.stat-icon {
  font-size: 12px;
}

.stat-value {
  font-weight: 500;
}

.node-handles {
  position: relative;
}

.handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #667eea;
  border: 2px solid white;
  border-radius: 50%;
  top: 50%;
  transform: translateY(-50%);
}

.handle-left {
  left: -6px;
}

.handle-right {
  right: -6px;
}
</style>
