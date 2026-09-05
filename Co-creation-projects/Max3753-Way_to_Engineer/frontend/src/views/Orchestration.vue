<template>
  <div class="orchestration-view">
    <div class="view-header">
      <div class="header-left">
        <h1>{{ langStore.t('orchestration.title') }}</h1>
        <p>{{ langStore.t('orchestration.subtitle') }}</p>
      </div>
      <div class="header-stats">
        <div class="stat-chip">
          <span class="stat-dot active"></span>
          <span>{{ agentStore.activeCount }} {{ langStore.t('orchestration.active') }}</span>
        </div>
        <div class="stat-chip">
          <span class="stat-dot total"></span>
          <span>{{ agentStore.totalMessages }} {{ langStore.t('orchestration.messages') }}</span>
        </div>
      </div>
    </div>
    
    <div class="flow-container">
      <VueFlow
        v-model="nodes"
        :edges="edges"
        :default-viewport="{ zoom: 1, x: 0, y: 0 }"
        :min-zoom="0.5"
        :max-zoom="2"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :elements-selectable="true"
        fit-view-on-init
        @node-click="handleNodeClick"
        @node-drag-stop="handleNodeDragStop"
      >
        <template #node-orchestrator="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="orchestrator" 
            :label="langStore.t('orchestration.agents.orchestrator')"
            :status="getAgentStatus('orchestrator')"
            :message-count="getAgentMessages('orchestrator')"
            :last-used="getAgentLastUsed('orchestrator')"
          />
        </template>
        
        <template #node-tutor="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="tutor" 
            :label="langStore.t('orchestration.agents.tutor')"
            :status="getAgentStatus('tutor')"
            :message-count="getAgentMessages('tutor')"
            :last-used="getAgentLastUsed('tutor')"
          />
        </template>
        
        <template #node-debug="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="debug" 
            :label="langStore.t('orchestration.agents.debug')"
            :status="getAgentStatus('debug')"
            :message-count="getAgentMessages('debug')"
            :last-used="getAgentLastUsed('debug')"
          />
        </template>
        
        <template #node-review="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="review" 
            :label="langStore.t('orchestration.agents.review')"
            :status="getAgentStatus('review')"
            :message-count="getAgentMessages('review')"
            :last-used="getAgentLastUsed('review')"
          />
        </template>
        
        <template #node-arch="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="arch" 
            :label="langStore.t('orchestration.agents.arch')"
            :status="getAgentStatus('arch')"
            :message-count="getAgentMessages('arch')"
            :last-used="getAgentLastUsed('arch')"
          />
        </template>
        
        <template #node-coach="nodeProps">
          <AgentNode 
            v-bind="nodeProps" 
            type="coach" 
            :label="langStore.t('orchestration.agents.coach')"
            :status="getAgentStatus('coach')"
            :message-count="getAgentMessages('coach')"
            :last-used="getAgentLastUsed('coach')"
          />
        </template>
        
        <Background />
        <Controls />
      </VueFlow>
    </div>
    
    <div class="info-panel">
      <div class="agent-list">
        <div 
          v-for="agent in agentStore.agents" 
          :key="agent.type"
          :class="['agent-item', agent.type, { active: agent.status === 'active' || agent.status === 'processing' }]"
          @click="openConfigPanel(agent.type)"
        >
          <div class="agent-icon-wrap">
            <span class="agent-icon">{{ agent.icon }}</span>
            <span v-if="agent.status === 'active' || agent.status === 'processing'" class="active-ring"></span>
          </div>
          <div class="agent-info">
            <div class="agent-header">
              <span class="agent-name">{{ agent.name }}</span>
              <span class="agent-status" :class="agent.status">{{ getAgentStatusText(agent.status) }}</span>
            </div>
            <span class="agent-desc">{{ agent.description }}</span>
            <div class="agent-meta">
              <span class="meta-item">
                <span class="meta-icon">💬</span>
                <span>{{ langStore.t('orchestration.messagesCount', { count: agent.messageCount }) }}</span>
              </span>
              <span class="meta-item">
                <span class="meta-icon">🕐</span>
                <span>{{ agentStore.formatLastUsed(agent.lastUsedAt) }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Configuration Panel -->
    <AgentConfigPanel
      :visible="configPanelVisible"
      :agent="configPanelAgent"
      @close="closeConfigPanel"
      @start-chat="handleStartChat"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { VueFlow, type GraphNode } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import AgentNode from '../components/AgentNode.vue'
import AgentConfigPanel from '../components/AgentConfigPanel.vue'
import { useAgentStore, type AgentState } from '../stores/agentStore'
import { useLangStore } from '../stores/langStore'
import { getAgentStatusText } from '../utils/helpers'

const agentStore = useAgentStore()
const langStore = useLangStore()

// ─── Agent data helpers ───

const getAgentStatus = (type: string) => {
  const agent = agentStore.getAgent(type)
  return agent?.status || 'idle'
}

const getAgentMessages = (type: string) => {
  const agent = agentStore.getAgent(type)
  return agent?.messageCount || 0
}

const getAgentLastUsed = (type: string) => {
  const agent = agentStore.getAgent(type)
  return agent?.lastUsedAt || null
}

// ─── Agent color map (for edge styling) ───

const AGENT_COLORS: Record<string, string> = {
  orchestrator: '#667eea',
  tutor: '#764ba2',
  debug: '#f5222d',
  review: '#52c41a',
  arch: '#fa8c16',
  coach: '#722ed1',
}

// ─── Nodes (with drag persistence) ───

const DEFAULT_POSITIONS: Record<string, { x: number; y: number }> = {
  orchestrator: { x: 350, y: 50 },
  tutor: { x: 100, y: 250 },
  debug: { x: 280, y: 250 },
  review: { x: 460, y: 250 },
  arch: { x: 640, y: 250 },
  coach: { x: 820, y: 250 },
}

const loadSavedPositions = (): Record<string, { x: number; y: number }> => {
  try {
    const saved = localStorage.getItem('orchestration-node-positions')
    if (saved) return JSON.parse(saved)
  } catch { /* ignore */ }
  return {}
}

const savedPositions = loadSavedPositions()

const nodes = ref([
  {
    id: 'orchestrator',
    type: 'orchestrator',
    position: savedPositions['orchestrator'] || DEFAULT_POSITIONS['orchestrator'],
    data: { label: langStore.t('orchestration.agents.orchestrator') }
  },
  {
    id: 'tutor',
    type: 'tutor',
    position: savedPositions['tutor'] || DEFAULT_POSITIONS['tutor'],
    data: { label: langStore.t('orchestration.agents.tutor') }
  },
  {
    id: 'debug',
    type: 'debug',
    position: savedPositions['debug'] || DEFAULT_POSITIONS['debug'],
    data: { label: langStore.t('orchestration.agents.debug') }
  },
  {
    id: 'review',
    type: 'review',
    position: savedPositions['review'] || DEFAULT_POSITIONS['review'],
    data: { label: langStore.t('orchestration.agents.review') }
  },
  {
    id: 'arch',
    type: 'arch',
    position: savedPositions['arch'] || DEFAULT_POSITIONS['arch'],
    data: { label: langStore.t('orchestration.agents.arch') }
  },
  {
    id: 'coach',
    type: 'coach',
    position: savedPositions['coach'] || DEFAULT_POSITIONS['coach'],
    data: { label: langStore.t('orchestration.agents.coach') }
  }
])

// ─── Edges (reactive to active agent) ───

const activeAgentType = computed(() => {
  const active = agentStore.agents.find(
    a => a.status === 'active' || a.status === 'processing'
  )
  return active?.type || null
})

const edgeDefinitions = [
  { id: 'e1', source: 'orchestrator', target: 'tutor' },
  { id: 'e2', source: 'orchestrator', target: 'debug' },
  { id: 'e3', source: 'orchestrator', target: 'review' },
  { id: 'e4', source: 'orchestrator', target: 'arch' },
  { id: 'e5', source: 'orchestrator', target: 'coach' },
]

const edges = computed(() => {
  return edgeDefinitions.map(def => {
    const isActive = activeAgentType.value === def.target
    const color = AGENT_COLORS[def.target] || '#b1b1b7'

    if (isActive) {
      return {
        ...def,
        type: 'smoothstep' as const,
        animated: true,
        style: {
          stroke: color,
          strokeWidth: 3,
          filter: `drop-shadow(0 0 6px ${color}66)`,
        },
        class: 'edge-active',
      }
    }

    return {
      ...def,
      type: 'smoothstep' as const,
      animated: false,
      style: {
        stroke: '#d1d5db',
        strokeWidth: 1.5,
      },
      class: '',
    }
  })
})

// ─── Drag persistence ───

const handleNodeDragStop = () => {
  const positions: Record<string, { x: number; y: number }> = {}
  nodes.value.forEach(node => {
    positions[node.id] = { ...node.position }
  })
  try {
    localStorage.setItem('orchestration-node-positions', JSON.stringify(positions))
  } catch { /* quota exceeded - ignore */ }
}

// ─── Config panel ───

const configPanelVisible = ref(false)
const configPanelAgentType = ref<string | null>(null)

const configPanelAgent = computed<AgentState | null>(() => {
  if (!configPanelAgentType.value) return null
  return agentStore.getAgent(configPanelAgentType.value) || null
})

const handleNodeClick = ({ node }: { node: GraphNode; event: MouseEvent }) => {
  configPanelAgentType.value = node.id
  configPanelVisible.value = true
}

const openConfigPanel = (type: string) => {
  configPanelAgentType.value = type
  configPanelVisible.value = true
}

const closeConfigPanel = () => {
  configPanelVisible.value = false
  configPanelAgentType.value = null
}

const handleStartChat = (agentType: string) => {
  // Store the intended agent for Chat.vue to optionally pick up
  try {
    sessionStorage.setItem('pendingAgentType', agentType)
  } catch { /* ignore */ }
  closeConfigPanel()
}

// ─── Reset positions on first load if none saved ───

onMounted(() => {
  if (!savedPositions || Object.keys(savedPositions).length === 0) {
    // First visit — positions are at defaults, nothing to restore
  }
})
</script>

<style scoped>
.orchestration-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: var(--bg-primary, #f8f9fa);
  overflow: hidden;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  background: var(--bg-secondary, white);
  border-bottom: 1px solid var(--border-color, #e5e5e5);
}

.header-left h1 {
  margin: 0 0 4px 0;
  font-size: 22px;
  color: var(--text-primary, #1a1a1a);
}

.header-left p {
  margin: 0;
  color: var(--text-secondary, #666);
  font-size: 13px;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-tertiary, #f5f7fa);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-dot.active {
  background: var(--success-color, #52c41a);
  animation: pulse 2s infinite;
}

.stat-dot.total {
  background: var(--accent-color, #667eea);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.flow-container {
  flex: 1;
  background: var(--bg-secondary, white);
  margin: 16px 32px;
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--shadow-color, rgba(0, 0, 0, 0.06));
  overflow: hidden;
  position: relative;
}

/* ─── Active edge glow (global style for VueFlow edges) ─── */
.flow-container :deep(.edge-active .vue-flow__edge-path) {
  filter: drop-shadow(0 0 8px currentColor);
}

.flow-container :deep(.vue-flow__edge.animated .vue-flow__edge-path) {
  stroke-dasharray: 8 4;
  animation: edge-flow 0.8s linear infinite;
}

@keyframes edge-flow {
  to { stroke-dashoffset: -12; }
}

.info-panel {
  padding: 0 32px 20px;
}

.agent-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.agent-item {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-secondary, white);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--shadow-color, rgba(0, 0, 0, 0.06));
  border: 1px solid var(--border-color, #e8e8e8);
  transition: all 0.2s;
  cursor: pointer;
}

.agent-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.agent-item.active {
  border-color: var(--accent-color, #667eea);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.agent-item.orchestrator.active { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
.agent-item.tutor.active { border-color: #764ba2; box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.1); }
.agent-item.debug.active { border-color: #f5222d; box-shadow: 0 0 0 3px rgba(245, 34, 45, 0.1); }
.agent-item.review.active { border-color: #52c41a; box-shadow: 0 0 0 3px rgba(82, 196, 26, 0.1); }
.agent-item.arch.active { border-color: #fa8c16; box-shadow: 0 0 0 3px rgba(250, 140, 22, 0.1); }
.agent-item.coach.active { border-color: #722ed1; box-shadow: 0 0 0 3px rgba(114, 46, 209, 0.1); }

.agent-icon-wrap {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.orchestrator .agent-icon-wrap { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.tutor .agent-icon-wrap { background: linear-gradient(135deg, #764ba2 0%, #9b59b6 100%); }
.debug .agent-icon-wrap { background: linear-gradient(135deg, #f5222d 0%, #cf1322 100%); }
.review .agent-icon-wrap { background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); }
.arch .agent-icon-wrap { background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%); }
.coach .agent-icon-wrap { background: linear-gradient(135deg, #722ed1 0%, #531dab 100%); }

.agent-icon {
  font-size: 22px;
}

.active-ring {
  position: absolute;
  inset: -3px;
  border: 2px solid currentColor;
  border-radius: 14px;
  animation: ring-pulse 1.5s infinite;
}

.orchestrator .active-ring { border-color: #667eea; }
.tutor .active-ring { border-color: #764ba2; }
.debug .active-ring { border-color: #f5222d; }
.review .active-ring { border-color: #52c41a; }
.arch .active-ring { border-color: #fa8c16; }
.coach .active-ring { border-color: #722ed1; }

@keyframes ring-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.05); }
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.agent-name {
  font-weight: 600;
  color: var(--text-primary, #1a1a1a);
  font-size: 14px;
}

.agent-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.agent-status.active {
  background: #f6ffed;
  color: #52c41a;
}

.agent-status.processing {
  background: #e6f7ff;
  color: #1890ff;
}

.agent-status.idle {
  background: #f5f5f5;
  color: #999;
}

.agent-status.error {
  background: #fff2f0;
  color: #ff4d4f;
}

.agent-desc {
  display: block;
  color: var(--text-muted, #999);
  font-size: 12px;
  margin-bottom: 6px;
}

.agent-meta {
  display: flex;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted, #999);
}

.meta-icon {
  font-size: 12px;
}
</style>
