import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

interface Persona {
    id: number
    name: string
    title: string
    bio: string
    theories: string[]
    stance: string
    system_prompt: string
    is_public: boolean
}

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    timestamp: number
    personas?: Persona[] // If assistant generated personas
}

export const useGodStore = defineStore('god', {
    state: () => ({
        messages: [] as ChatMessage[],
        loading: false
    }),
    actions: {
        async sendMessage(prompt: string) {
            // Add user message
            this.messages.push({
                role: 'user',
                content: prompt,
                timestamp: Date.now()
            })

            this.loading = true
            let retries = 0
            const maxRetries = 2

            while (retries <= maxRetries) {
                try {
                    // Call backend with extended timeout (120s)
                    const response = await fetch('/api/v1/god/generate_real', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${localStorage.getItem('token') || ''}`
                        },
                        body: JSON.stringify({ prompt, n: 1 })
                    })
                    if (!response.ok || !response.body) throw new Error(`God generation failed: ${response.status}`)
                    const reader = response.body.getReader()
                    const decoder = new TextDecoder()
                    let buffer = ''
                    const personas: Persona[] = []
                    while (true) {
                        const { done, value } = await reader.read()
                        if (done) break
                        buffer += decoder.decode(value, { stream: true })
                        const parts = buffer.split('\n\n')
                        buffer = parts.pop() || ''
                        for (const part of parts) {
                            if (!part.startsWith('data: ')) continue
                            const event = JSON.parse(part.slice(6))
                            if (event.type === 'result') {
                                const result = Array.isArray(event.content) ? event.content : [event.content]
                                personas.push(...result)
                            }
                            if (event.type === 'error') throw new Error(event.content || 'God generation failed')
                        }
                    }

                    // Add assistant response
                    this.messages.push({
                        role: 'assistant',
                        content: `已为您生成 ${personas.length} 位智能体角色。`,
                        timestamp: Date.now(),
                        personas: personas
                    })
                    
                    message.success('生成成功')
                    break // Success, exit loop
                } catch (error: any) {
                    console.error(`God generation attempt ${retries + 1} failed:`, error)
                    
                    if (retries === maxRetries) {
                        // All retries failed
                        throw error // Re-throw to be caught by the view
                    }
                    
                    retries++
                    // Wait 1s before retry
                    await new Promise(resolve => setTimeout(resolve, 1000))
            }
        }
        
        this.loading = false
    },
        clearHistory() {
            this.messages = []
        }
    }
})
