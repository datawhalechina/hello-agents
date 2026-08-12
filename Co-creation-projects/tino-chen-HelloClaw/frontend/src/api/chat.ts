import api from './index'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  content: string
  session_id: string | null
}

export interface StreamEvent {
  type: 'session' | 'step_start' | 'chunk' | 'tool_start' | 'tool_finish' | 'step_finish' | 'done' | 'error'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  error?: string
  session_id?: string | null
  step?: number
  max_steps?: number
}

export type StreamCallback = (event: StreamEvent) => void

export const chatApi = {
  // 流式发送消息 (SSE)
  sendMessage: async (message: string, sessionId?: string) => {
    return api.post('/chat/send', { message, session_id: sessionId })
  },

  // 同步发送消息（支持取消，超时时间 5 分钟）
  sendMessageSync: async (
    message: string,
    sessionId?: string,
    signal?: AbortSignal
  ): Promise<ChatResponse> => {
    return api.post('/chat/send/sync', { message, session_id: sessionId }, {
      signal,
      timeout: 300000, // 5 分钟超时
    })
  },

  // 流式发送消息 (SSE) - 返回完整响应
  sendMessageStream: async (
    message: string,
    sessionId: string | null | undefined,
    onChunk: StreamCallback,
    signal?: AbortSignal
  ): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/api/chat/send/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let fullContent = ''
    let finalSessionId = sessionId

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 事件
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          // 跳过 ping 事件和空行
          if (line.startsWith('ping') || line.trim() === '') {
            continue
          }

          if (line.startsWith('event:')) {
            currentEvent = line.substring(6).trim()
          } else if (line.startsWith('data:')) {
            const data = line.substring(5).trim()
            if (data && currentEvent) {
              try {
                const parsed = JSON.parse(data)

                if (currentEvent === 'session') {
                  finalSessionId = parsed.session_id
                  onChunk({ type: 'session', session_id: parsed.session_id })
                } else if (currentEvent === 'step_start') {
                  onChunk({ type: 'step_start', step: parsed.step, max_steps: parsed.max_steps })
                } else if (currentEvent === 'chunk') {
                  fullContent += parsed.content || ''
                  onChunk({ type: 'chunk', content: parsed.content })
                } else if (currentEvent === 'tool_start') {
                  onChunk({ type: 'tool_start', tool: parsed.tool, args: parsed.args })
                } else if (currentEvent === 'tool_finish') {
                  onChunk({ type: 'tool_finish', tool: parsed.tool, result: parsed.result })
                } else if (currentEvent === 'step_finish') {
                  onChunk({ type: 'step_finish', step: parsed.step })
                } else if (currentEvent === 'done') {
                  finalSessionId = parsed.session_id
                  onChunk({ type: 'done', content: parsed.content, session_id: parsed.session_id })
                } else if (currentEvent === 'error') {
                  onChunk({ type: 'error', error: parsed.error })
                }
              } catch {
                // 忽略解析错误
              }
              currentEvent = ''
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }

    return { content: fullContent, session_id: finalSessionId ?? null }
  },
}
