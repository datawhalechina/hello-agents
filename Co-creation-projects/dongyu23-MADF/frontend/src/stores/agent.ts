import { defineStore } from 'pinia'
import axios from 'axios'

interface AgentConfig {
  name: string
  bio: string
  theories: string[]
  stance: string
}

interface ChatMessage {
  speaker: string
  content: string
}

interface AgentThought {
  action: string
  thought: string
  target?: string
}

export const useAgentStore = defineStore('agent', {
  state: () => ({
    agentConfig: {
      name: 'Socrates',
      bio: 'Ancient Greek philosopher, founder of the Socratic method.',
      theories: ['Maieutics', 'Irony', 'Dialectic'],
      stance: 'Neutral'
    } as AgentConfig,
    context: [] as ChatMessage[],
    theme: 'The impact of AI on the future',
    loading: false,
    error: null as string | null,
    lastThought: null as AgentThought | null
  }),
  actions: {
    async chat(userInstruction: string) {
      this.loading = true
      this.error = null
      
      // Add user instruction to context
      this.context.push({ speaker: 'User', content: userInstruction })
      
      try {
        const payload = {
          agent_name: this.agentConfig.name,
          persona_json: {
            name: this.agentConfig.name,
            bio: this.agentConfig.bio,
            theories: this.agentConfig.theories,
            stance: this.agentConfig.stance
          },
          context_messages: this.context,
          theme: this.theme
        }
        
        const response = await axios.post('/api/v1/agents/chat', payload)
        
        if (response.data) {
          this.lastThought = response.data.thought
          if (response.data.content) {
            this.context.push({ speaker: this.agentConfig.name, content: response.data.content })
          } else if (response.data.thought?.action === 'listen') {
            this.context.push({ speaker: 'System', content: `${this.agentConfig.name} is listening...` })
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error) {
            this.error = err.message
        } else {
            this.error = 'An error occurred'
        }
      } finally {
        this.loading = false
      }
    },
    reset() {
      this.context = []
      this.lastThought = null
      this.error = null
    }
  }
})
