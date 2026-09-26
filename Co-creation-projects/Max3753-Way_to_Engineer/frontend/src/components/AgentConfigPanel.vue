<template>
  <Teleport to="body">
    <Transition name="panel-overlay">
      <div v-if="visible" class="config-overlay" @click.self="$emit('close')"></div>
    </Transition>
    <Transition name="panel-slide">
      <div v-if="visible && agent" class="config-panel">
        <div class="panel-header" :class="agent.type">
          <div class="header-top">
            <div class="header-identity">
              <span class="panel-icon">{{ agent.icon }}</span>
              <div class="header-text">
                <h2>{{ agent.name }}</h2>
                <span class="panel-type">{{ agent.type }}</span>
              </div>
            </div>
            <button class="close-btn" @click="$emit('close')" title="Close">
              <span class="close-icon">&times;</span>
            </button>
          </div>
          <div class="status-row">
            <span class="status-badge" :class="agent.status">
              <span class="status-dot"></span>
              {{ statusLabel }}
            </span>
            <span class="message-count">{{ agent.messageCount }} messages</span>
          </div>
        </div>

        <div class="panel-body">
          <section class="config-section">
            <h3 class="section-title">Description</h3>
            <p class="section-text">{{ agent.description }}</p>
          </section>

          <section class="config-section">
            <h3 class="section-title">System Prompt</h3>
            <div class="prompt-block">
              <pre class="prompt-text">{{ systemPrompt }}</pre>
            </div>
          </section>

          <section class="config-section">
            <h3 class="section-title">Activity</h3>
            <div class="activity-grid">
              <div class="activity-card">
                <span class="activity-value">{{ agent.messageCount }}</span>
                <span class="activity-label">Messages</span>
              </div>
              <div class="activity-card">
                <span class="activity-value">{{ lastUsedDisplay }}</span>
                <span class="activity-label">Last Active</span>
              </div>
            </div>
          </section>

          <section v-if="agent.lastMessage" class="config-section">
            <h3 class="section-title">Last Conversation</h3>
            <div class="last-message">
              <span class="msg-preview">{{ agent.lastMessage }}</span>
            </div>
          </section>
        </div>

        <div class="panel-footer">
          <button class="action-btn primary" @click="startConversation">
            <span class="btn-icon">💬</span>
            Start Conversation
          </button>
          <button class="action-btn secondary" @click="$emit('close')">
            Close
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { AgentState } from '../stores/agentStore'

const props = defineProps<{
  visible: boolean
  agent: AgentState | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'start-chat', type: string): void
}>()

const router = useRouter()

const SYSTEM_PROMPTS: Record<string, string> = {
  orchestrator: 'You are the orchestrator agent. Your role is to analyze user requests and route them to the most appropriate specialist agent. You coordinate the workflow between tutors, debuggers, reviewers, architects, and coaches to provide comprehensive assistance.',
  tutor: 'You are a programming tutor. Your role is to explain programming concepts clearly and concisely. Use examples, analogies, and step-by-step explanations. Adapt your teaching style to the student\'s level. Encourage understanding over memorization.',
  debug: 'You are a debugging specialist. Your role is to analyze error messages, trace bugs, and provide clear fixes. Always explain the root cause before the solution. Help users understand why the bug occurred and how to prevent similar issues.',
  review: 'You are a code reviewer. Your role is to analyze code for quality, best practices, security issues, and potential improvements. Be constructive and specific in your feedback. Prioritize issues by severity.',
  arch: 'You are a software architect. Your role is to help design system architecture, make technology choices, and plan scalable solutions. Consider trade-offs and explain the reasoning behind architectural decisions.',
  coach: 'You are a learning coach. Your role is to guide users through their learning journey. Create personalized learning paths, track progress, and provide encouragement. Focus on practical skills and real-world application.',
}

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    active: 'Active',
    processing: 'Processing',
    idle: 'Idle',
    error: 'Error',
  }
  return labels[props.agent?.status || 'idle'] || 'Idle'
})

const systemPrompt = computed(() => {
  if (!props.agent) return ''
  return SYSTEM_PROMPTS[props.agent.type] || 'No system prompt configured.'
})

const lastUsedDisplay = computed(() => {
  if (!props.agent?.lastUsedAt) return 'Never'
  const diff = Date.now() - props.agent.lastUsedAt
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return `${Math.floor(diff / 86400000)}d ago`
})

const startConversation = () => {
  if (props.agent) {
    emit('start-chat', props.agent.type)
    router.push('/')
  }
}
</script>

<style scoped>
/* ─── Overlay ─── */
.config-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 900;
  backdrop-filter: blur(2px);
}

/* ─── Panel ─── */
.config-panel {
  position: fixed;
  top: 56px;
  right: 0;
  bottom: 0;
  width: 380px;
  background: var(--bg-secondary, #ffffff);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
  z-index: 910;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ─── Header ─── */
.panel-header {
  padding: 24px 24px 16px;
  color: white;
  position: relative;
}

.panel-header.orchestrator { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.panel-header.tutor { background: linear-gradient(135deg, #764ba2 0%, #9b59b6 100%); }
.panel-header.debug { background: linear-gradient(135deg, #f5222d 0%, #cf1322 100%); }
.panel-header.review { background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); }
.panel-header.arch { background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%); }
.panel-header.coach { background: linear-gradient(135deg, #722ed1 0%, #531dab 100%); }

.header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.header-identity {
  display: flex;
  align-items: center;
  gap: 14px;
}

.panel-icon {
  font-size: 32px;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 14px;
}

.header-text h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.panel-type {
  font-size: 12px;
  opacity: 0.75;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.35);
}

.close-icon {
  font-size: 20px;
  line-height: 1;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.2);
}

.status-badge .status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
}

.status-badge.active .status-dot {
  background: #b7eb8f;
  animation: dot-pulse 1.5s infinite;
}

.status-badge.processing .status-dot {
  background: #91d5ff;
  animation: dot-pulse 1s infinite;
}

.status-badge.idle .status-dot {
  background: rgba(255, 255, 255, 0.4);
}

.status-badge.error .status-dot {
  background: #ffa39e;
}

.message-count {
  font-size: 12px;
  opacity: 0.8;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.4); }
}

/* ─── Body ─── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.config-section {
  margin-bottom: 24px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 10px 0;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--text-muted, #999);
}

.section-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary, #333);
}

.prompt-block {
  background: var(--bg-tertiary, #f0f2f5);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid var(--border-color, #e8e8e8);
}

.prompt-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--text-secondary, #666);
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.activity-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.activity-card {
  background: var(--bg-tertiary, #f0f2f5);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: center;
  border: 1px solid var(--border-color, #e8e8e8);
}

.activity-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #333);
  margin-bottom: 2px;
}

.activity-label {
  display: block;
  font-size: 11px;
  color: var(--text-muted, #999);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.last-message {
  background: var(--bg-tertiary, #f0f2f5);
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid var(--border-color, #e8e8e8);
}

.msg-preview {
  font-size: 13px;
  color: var(--text-secondary, #666);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── Footer ─── */
.panel-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #e8e8e8);
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.action-btn.secondary {
  background: var(--bg-tertiary, #f0f2f5);
  color: var(--text-secondary, #666);
  border: 1px solid var(--border-color, #e8e8e8);
}

.action-btn.secondary:hover {
  background: var(--border-color, #e8e8e8);
}

.btn-icon {
  font-size: 16px;
}

/* ─── Transitions ─── */
.panel-overlay-enter-active,
.panel-overlay-leave-active {
  transition: opacity 0.3s ease;
}

.panel-overlay-enter-from,
.panel-overlay-leave-to {
  opacity: 0;
}

.panel-slide-enter-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.panel-slide-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  transform: translateX(100%);
}
</style>
