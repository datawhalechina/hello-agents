import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface AgentState {
  type: string
  name: string
  icon: string
  description: string
  status: 'active' | 'idle' | 'error' | 'processing'
  messageCount: number
  lastUsedAt: number | null
  lastMessage: string
}

export const useAgentStore = defineStore('agents', () => {
  const agents = ref<AgentState[]>([
    {
      type: 'orchestrator',
      name: '编排器',
      icon: '🧠',
      description: '路由和协调',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    },
    {
      type: 'tutor',
      name: '编程导师',
      icon: '👨‍🏫',
      description: '概念讲解答疑',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    },
    {
      type: 'debug',
      name: '调试助手',
      icon: '🐛',
      description: '错误分析修复',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    },
    {
      type: 'review',
      name: '代码审查员',
      icon: '🔍',
      description: '代码质量审查',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    },
    {
      type: 'arch',
      name: '架构师',
      icon: '🏗️',
      description: '架构设计咨询',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    },
    {
      type: 'coach',
      name: '学习教练',
      icon: '🎯',
      description: '学习路径规划',
      status: 'idle',
      messageCount: 0,
      lastUsedAt: null,
      lastMessage: ''
    }
  ])

  const activeCount = computed(() =>
    agents.value.filter(a => a.status === 'active' || a.status === 'processing').length
  )

  const totalMessages = computed(() =>
    agents.value.reduce((sum, a) => sum + a.messageCount, 0)
  )

  const getAgent = (type: string) =>
    agents.value.find(a => a.type === type)

  const setAgentStatus = (type: string, status: AgentState['status']) => {
    const agent = getAgent(type)
    if (agent) {
      agent.status = status
      if (status === 'active' || status === 'processing') {
        agent.lastUsedAt = Date.now()
      }
    }
  }

  const recordMessage = (type: string, message: string) => {
    const agent = getAgent(type)
    if (agent) {
      agent.messageCount++
      agent.lastMessage = message.slice(0, 50)
      agent.lastUsedAt = Date.now()
    }
  }

  const setActiveAgent = (type: string) => {
    // Reset all to idle first
    agents.value.forEach(a => {
      if (a.status === 'active') a.status = 'idle'
    })
    // Set target as active
    setAgentStatus(type, 'active')
  }

  const resetAllStatus = () => {
    agents.value.forEach(a => {
      if (a.status !== 'error') a.status = 'idle'
    })
  }

  const formatLastUsed = (timestamp: number | null): string => {
    if (!timestamp) return '从未使用'
    const diff = Date.now() - timestamp
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    return `${Math.floor(diff / 86400000)}天前`
  }

  return {
    agents,
    activeCount,
    totalMessages,
    getAgent,
    setAgentStatus,
    recordMessage,
    setActiveAgent,
    resetAllStatus,
    formatLastUsed
  }
})
