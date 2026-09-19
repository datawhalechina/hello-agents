import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

export interface Message {
  id: number
  forum_id: number
  persona_id: number
  moderator_id?: number | null
  speaker_name: string
  content: string
  thought?: string | null // Added thought field
  timestamp: string
}

export interface Moderator {
  id: number
  name: string
  title: string
  bio: string
  system_prompt?: string
  greeting_template?: string
  closing_template?: string
  summary_template?: string
  creator_id: number
  created_at: string
}

export interface Forum {
  id: number
  topic: string
  creator_id: number
  moderator_id?: number | null
  moderator?: Moderator | null
  status: string
  start_time?: string | null
  summary_history: string[]
  participants?: any[]
  duration_minutes?: number
}

export interface SystemLog {
  id?: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'thought' | 'speech'
  content: string
  source?: string
}

export const useForumStore = defineStore('forum', {
  state: () => ({
    forums: [] as Forum[],
    currentForum: null as Forum | null,
    messages: [] as Message[],
    moderators: [] as Moderator[],
    systemLogs: [] as SystemLog[],
    loading: false,
    thinking: false,
    
    // WebSocket Global State
    ws: null as WebSocket | null,
    isConnected: false,
    wsForumId: null as number | null,
    heartbeatInterval: null as any,
    reconnectTimeout: null as any,
    reconnectAttempts: 0,
    isManuallyClosed: false
  }),
  actions: {
    systemLogKey(log: SystemLog) {
        const timestamp = new Date(log.timestamp).getTime()
        return `${timestamp}|${log.level}|${log.source || ''}|${log.content}`
    },
    mergeSystemLogs(...collections: SystemLog[][]) {
        const unique = new Map<string, SystemLog>()
        for (const log of collections.flat()) {
            const key = this.systemLogKey(log)
            const existing = unique.get(key)
            if (!existing || (existing.id == null && log.id != null)) {
                unique.set(key, log)
            }
        }
        return [...unique.values()].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
    },
    // --- Persistence ---
    saveToStorage() {
        if (!this.currentForum) return
        const data = {
            forum: this.currentForum,
            messages: this.messages,
            logs: this.systemLogs,
            thinking: this.thinking,
            timestamp: Date.now()
        }
        try {
            localStorage.setItem(`forum_data_${this.currentForum.id}`, JSON.stringify(data))
        } catch (e) {
            console.error('Failed to save to storage', e)
        }
    },

    loadFromStorage(forumId: number): boolean {
        try {
            const raw = localStorage.getItem(`forum_data_${forumId}`)
            if (!raw) return false
            const data = JSON.parse(raw)
            
            // Validate data integrity
            // Must have a valid forum object with ID matching request
            if (!data.forum || data.forum.id !== forumId) {
                return false
            }
            
            this.currentForum = data.forum
            // Ensure messages are valid (must have speaker_name)
            this.messages = Array.isArray(data.messages) 
                ? data.messages.filter((m: any) => m && typeof m.speaker_name === 'string') 
                : []
            this.systemLogs = Array.isArray(data.logs) ? data.logs : []
            this.thinking = !!data.thinking
            return true
        } catch (e) {
            console.error('Failed to load from storage', e)
            return false
        }
    },

    // --- WebSocket Actions ---
    resolveWsBase() {
        const raw = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim()
        if (!raw) {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
          return `${protocol}//${window.location.host}`
        }
        if (raw.startsWith('ws://') || raw.startsWith('wss://')) {
          return raw.replace(/\/$/, '')
        }
        if (raw.startsWith('http://') || raw.startsWith('https://')) {
          return raw.replace(/^http/, 'ws').replace(/\/$/, '')
        }
        return raw.replace(/\/$/, '')
    },
    
    clearTimers() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval)
        if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout)
        this.heartbeatInterval = null
        this.reconnectTimeout = null
    },

    disconnectWebSocket() {
        this.isManuallyClosed = true
        this.clearTimers()
        if (this.ws) {
            try {
                // Remove listeners to prevent reconnect loops on manual close
                this.ws.onclose = null
                this.ws.onerror = null
                this.ws.onmessage = null
                this.ws.onopen = null
                this.ws.close(1000, "Client initiated disconnect")
            } catch (e) { /* ignore */ }
            this.ws = null
            this.isConnected = false
            this.wsForumId = null
        }
    },

    connectWebSocket(forumId: number) {
        // If already connected to this forum, just return
        if (this.ws && this.isConnected && this.wsForumId === forumId && this.ws.readyState === WebSocket.OPEN) {
            return
        }

        // If connected to a DIFFERENT forum, disconnect first
        if (this.ws && (this.wsForumId !== forumId || this.ws.readyState !== WebSocket.OPEN)) {
            this.disconnectWebSocket()
        }

        // Start new connection
        this.isManuallyClosed = false
        this.wsForumId = forumId
        const wsBase = this.resolveWsBase()
        const token = localStorage.getItem('token')
        const wsUrl = `${wsBase}/api/v1/forums/${forumId}/ws${token ? `?token=${encodeURIComponent(token)}` : ''}`
        const maxReconnectAttempts = 10

        console.log(`[WS Global] Connecting to forum ${forumId}`)

        try {
            this.ws = new WebSocket(wsUrl)
            
            this.ws.onopen = () => {
                console.log('[WS Global] Connected successfully')
                this.isConnected = true
                this.reconnectAttempts = 0
                
                // Sync data on connect
                this.fetchMessages(forumId)
                
                this.clearTimers()
                
                // Heartbeat
                this.heartbeatInterval = setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('ping')
                    }
                }, 30000)
            }
            
            this.ws.onmessage = (event) => {
                try {
                    if (event.data === 'pong') return
                    
                    const data = JSON.parse(event.data)
                    
                    if (data.type === 'new_message' && data.data) {
                        this.addMessage(data.data)
                    } else if (data.type === 'message_chunk' && data.data) {
                        this.updateStreamingMessage(data.data)
                    } else if (data.type === 'system_log' && data.data) {
                        this.addSystemLog(data.data)
                    } else if (data.type === 'system' && data.content) {
                        this.addSystemLog({
                            timestamp: new Date().toISOString(),
                            level: 'info',
                            content: data.content,
                            source: 'System'
                        })
                    } else if (data.type === 'status_update' && data.status && this.currentForum) {
                        this.currentForum.status = data.status
                        this.thinking = data.status === 'running'
                    }
                } catch (e) {
                    console.error('[WS Global] Parse Error', e)
                }
            }
            
            this.ws.onclose = (e) => {
                console.log(`[WS Global] Closed (Code: ${e.code})`)
                this.isConnected = false
                this.clearTimers()
                
                if (!this.isManuallyClosed && this.reconnectAttempts < maxReconnectAttempts) {
                    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
                    console.log(`[WS Global] Reconnecting in ${delay}ms...`)
                    
                    this.reconnectTimeout = setTimeout(() => {
                        this.reconnectAttempts++
                        // Recursive call via store instance? 
                        // We are inside action, so 'this' is store.
                        // But setTimeout changes context. Need to capture 'this' or use arrow.
                        this.connectWebSocket(forumId)
                    }, delay)
                }
            }
            
            this.ws.onerror = () => {
                console.warn('[WS Global] Connection error')
            }
            
        } catch (e) {
            console.error('[WS Global] Connection Failed', e)
        }
    },
    
    async fetchSystemLogs(forumId: number) {
      try {
        const res = await request.get(`/forums/${forumId}/logs`)
        
        if (Array.isArray(res.data)) {
            const backendLogs = res.data as SystemLog[]
            
            // Smart Merge Strategy:
            // 1. Trust Backend Logs as base history.
            // 2. Keep Local Logs that are NOT present in Backend Logs (likely pending persistence).
            
            // Create signature set for O(1) lookup
            // Signature = timestamp + content (source/level might vary slightly but usually consistent)
            this.systemLogs = this.mergeSystemLogs(backendLogs, this.systemLogs)
            
        } else {
             // If response is invalid, keep local logs
             console.warn('Invalid logs response', res.data)
        }
        
        // Restore "thinking" or "speaking" state based on last log
        if (this.systemLogs.length > 0) {
            const lastLog = this.systemLogs[this.systemLogs.length - 1]
            if (lastLog.level === 'thought' || lastLog.content.includes('正在思考')) {
                this.thinking = true
            } else {
                this.thinking = false
            }
        }
      } catch (error) {
        console.error('Failed to fetch system logs:', error)
      }
    },
    addSystemLog(log: SystemLog) {
        this.systemLogs = this.mergeSystemLogs(this.systemLogs, [log])
    },
    updateStreamingMessage(chunk: { 
        speaker_name: string, 
        content: string, 
        persona_id: number | null, 
        moderator_id?: number | null, 
        stream_id?: string, 
        thought?: string | null,
        timestamp: string 
    }) {
        if (!this.currentForum) return // Guard against updates when no forum loaded
        
        // Robust logic: Use stream_id if available to find the message
        // If stream_id is missing, fallback to last message match (legacy behavior)
        
        let targetMsg: Message | undefined
        
        if (chunk.stream_id) {
            targetMsg = this.messages.find(m => (m as any).stream_id === chunk.stream_id)
        } else {
            // Fallback: Check last message
            const lastMsg = this.messages[this.messages.length - 1]
            if (lastMsg && lastMsg.speaker_name === chunk.speaker_name && (lastMsg as any).isStreaming) {
                targetMsg = lastMsg
            }
        }
        
        if (targetMsg) {
            targetMsg.content += (chunk.content || '')
            // Thought usually comes with the first chunk or separately, update if present
            if (chunk.thought && !targetMsg.thought) {
                targetMsg.thought = chunk.thought
            }
        } else {
            // Start new streaming message
            const newMsg: Message = {
                id: Date.now(), // Temp ID, will be replaced by final message
                forum_id: this.currentForum?.id || 0,
                persona_id: chunk.persona_id || 0,
                moderator_id: chunk.moderator_id || null,
                speaker_name: chunk.speaker_name || 'Unknown',
                content: chunk.content || '',
                thought: chunk.thought, // Initialize thought
                timestamp: chunk.timestamp || new Date().toISOString(),
            }
            ;(newMsg as any).isStreaming = true
            ;(newMsg as any).stream_id = chunk.stream_id // Store stream_id for future chunks
            this.messages.push(newMsg)
        }
        
        // Throttle save for streaming (save every ~50 chars or just rely on manual save on exit?)
        // To be safe and meet "long time retention", let's save occasionally
        if (Math.random() < 0.1) { // 10% chance to save on chunk update
             this.saveToStorage()
        }
    },
    addMessage(msg: Message & { stream_id?: string }) {
        if (!this.currentForum) return // Guard against updates when no forum loaded
        
        // When the full message arrives (type: 'new_message'), replace the streaming one
        // Match by stream_id if available, otherwise fallback
        
        let streamingMsgIndex = -1
        
        if (msg.stream_id) {
            streamingMsgIndex = this.messages.findIndex(m => (m as any).stream_id === msg.stream_id)
        }
        
        // Fallback match if stream_id not found or not provided
        if (streamingMsgIndex === -1) {
             streamingMsgIndex = this.messages.findIndex(m => m.speaker_name === msg.speaker_name && (m as any).isStreaming)
        }
        
        if (streamingMsgIndex !== -1) {
            // Replace streaming message with the final one
            this.messages.splice(streamingMsgIndex, 1, msg)
        } else {
             // Check if message already exists by ID to prevent duplicates
             const exists = this.messages.find(m => m.id === msg.id)
             if (!exists) {
                 this.messages.push(msg)
             }
        }
        
        this.saveToStorage() // Always save on full message
        // Auto-scroll logic could be triggered here or in component watcher
    },
    async fetchForums() {
      // Background update if data exists
      const isBackground = this.forums.length > 0
      if (!isBackground) {
          this.loading = true
      }
      try {
        const res = await request.get('/forums/', { params: { limit: 500 } })
        this.forums = res.data
      } catch (error) {
        console.error('Failed to fetch forums:', error)
      } finally {
        this.loading = false
      }
    },
    async fetchForum(id: number) {
        // 1. Check if ID is valid
        if (!id || isNaN(id)) {
            console.error('Invalid forum ID', id)
            this.currentForum = null
            return
        }

        // 2. Memory Cache: If we already have THIS forum loaded, just refresh it
        if (this.currentForum && this.currentForum.id === id) {
            this.refreshForumData(id) 
            return
        }

        // 3. Switching or Initial Load: ALWAYS clear old data first to prevent ghosting
        this.clearForumData()

        // 4. Storage Cache: Try to load from localStorage
        if (this.loadFromStorage(id)) {
            // If loaded from storage, we can show it immediately
            // But if it's 'pending', we don't even need to refresh messages/logs
            if (this.currentForum?.status !== 'pending') {
                this.refreshForumData(id)
            }
            return
        }

        // 5. Fresh Load from Network
        this.loading = true
        try {
            // First, get the forum metadata to check status
            const forumRes = await request.get(`/forums/${id}`)
            if (!forumRes.data) throw new Error('Empty response')
            
            this.currentForum = forumRes.data

            // If forum is 'pending', it's brand new or hasn't started, no need to fetch messages/logs
            if (this.currentForum?.status !== 'pending') {
                const [messagesRes, logsRes] = await Promise.all([
                    request.get(`/forums/${id}/messages`).catch(e => ({ data: [] })),
                    request.get(`/forums/${id}/logs`).catch(e => ({ data: [] }))
                ])

                // Process messages
                if (Array.isArray(messagesRes.data)) {
                     this.messages = messagesRes.data.filter((m: any) => m && typeof m.speaker_name === 'string')
                }

                // Process logs
                if (Array.isArray(logsRes.data)) {
                    this.systemLogs = logsRes.data
                }
                
                // Restore thinking state
                this.updateThinkingState()
            } else {
                // Brand new or pending forum - ensure clean state
                this.messages = []
                this.systemLogs = []
                this.thinking = false
            }

            this.saveToStorage()
      } catch (error) {
            const status = (error as { response?: { status?: number } })?.response?.status
            if (status !== 401 && status !== 403 && status !== 404) {
                console.error(`Failed to fetch forum ${id}:`, error)
            }
            this.currentForum = null
        } finally {
            this.loading = false
        }
    },

    updateThinkingState() {
        if (this.systemLogs.length > 0) {
            const lastLog = this.systemLogs[this.systemLogs.length - 1]
            if (lastLog.level === 'thought' || lastLog.content.includes('正在思考')) {
                this.thinking = true
            } else {
                this.thinking = false
            }
        } else {
            this.thinking = false
        }
    },

    async refreshForumData(id: number) {
        // Background refresh logic
        try {
            const forumRes = await request.get(`/forums/${id}`).catch(e => null)
            if (!forumRes || !forumRes.data) return

            // Only update if we are still on the same forum
            if (!this.currentForum || this.currentForum.id !== id) return
            
            this.currentForum = { ...this.currentForum, ...forumRes.data }

            // Only fetch messages/logs if NOT pending
            if (this.currentForum.status !== 'pending') {
                const [messagesRes, logsRes] = await Promise.all([
                    request.get(`/forums/${id}/messages`).catch(e => null),
                    request.get(`/forums/${id}/logs`).catch(e => null)
                ])

                if (messagesRes && Array.isArray(messagesRes.data)) {
                     this.messages = messagesRes.data.filter((m: any) => m && typeof m.speaker_name === 'string')
                }

                if (logsRes && Array.isArray(logsRes.data)) {
                    this.systemLogs = logsRes.data
                    this.updateThinkingState()
                }
            }

            this.saveToStorage()
        } catch (e) {
            console.error('Background fetch failed', e)
        }
    },
    async fetchMessages(forumId: number) {
      try {
        const res = await request.get(`/forums/${forumId}/messages`)
        // Validate array
        if (Array.isArray(res.data)) {
            // Filter invalid messages
            this.messages = res.data.filter((m: any) => m && typeof m.speaker_name === 'string')
        } else {
            console.warn('Invalid messages format', res.data)
            this.messages = []
        }
        
        await this.fetchSystemLogs(forumId)
        
        // Save after successful fetch to keep storage fresh
        if (this.currentForum && this.currentForum.id === forumId) {
             this.saveToStorage()
        }
      } catch (error) {
        console.error(`Failed to fetch messages for forum ${forumId}:`, error)
        // Do not clear messages on error to keep cache displayed
      }
    },
    async fetchModerators() {
      try {
        const res = await request.get('/moderators/')
        this.moderators = res.data
      } catch (error) {
        console.error('Failed to fetch moderators:', error)
        this.moderators = []
      }
    },
    async createForum(topic: string, participantIds: number[], duration: number, moderatorId?: number) {
      this.loading = true
      try {
        const normalizedParticipantIds = Array.from(
          new Set(
            participantIds
              .map(id => Number(id))
              .filter(id => Number.isInteger(id) && id > 0)
          )
        )
        const res = await request.post('/forums/', {
          topic,
          participant_ids: normalizedParticipantIds,
          moderator_id: moderatorId,
          duration_minutes: duration
        })
        message.success('论坛创建成功')
        // Optimistic update: Add to list immediately
        this.forums.unshift(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to create forum:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async startForum(id: number) {
      try {
        const res = await request.post(`/forums/${id}/start`)
        message.success('论坛已开始')
        if (this.currentForum && this.currentForum.id === id) {
            this.currentForum.status = 'running'
            if (res.data?.start_time) this.currentForum.start_time = res.data.start_time
            if (res.data?.duration_minutes) this.currentForum.duration_minutes = res.data.duration_minutes
        }
      } catch (error) {
        console.error('Failed to start forum:', error)
        message.error('启动失败')
      }
    },
    async deleteForum(id: number) {
      // Optimistic update: Remove locally first
      const previousForums = [...this.forums]
      const previousCurrentForum = this.currentForum
      
      this.forums = this.forums.filter(f => f.id !== id)
      
      // Clear memory if deleting current
      if (this.currentForum && this.currentForum.id === id) {
           this.clearForumData()
      }
      
      try {
        await request.delete(`/forums/${id}`)
        // Clean storage
        localStorage.removeItem(`forum_data_${id}`)
      } catch (error) {
        console.error('Failed to delete forum:', error)
        // Rollback on failure
        this.forums = previousForums
        this.currentForum = previousCurrentForum
        // Also restore storage if needed? (Too complex, assume delete failure implies data still exists)
        throw error
      }
    },
    // New Action: Stop Forum
    async stopForum(id: number) {
        try {
            await request.post(`/forums/${id}/stop`)
            // Update local status if applicable
            const f = this.forums.find(f => f.id === id)
            if (f) f.status = 'closed'
            if (this.currentForum && this.currentForum.id === id) {
                this.currentForum.status = 'closed'
            }
            message.success('论坛已停止')
        } catch (error) {
            console.error('Failed to stop forum:', error)
            message.error('停止失败')
        }
    },
    leaveForum() {
      // Save current state before leaving
      this.saveToStorage()
      
      // Don't clear messages immediately to prevent flicker when switching
      // But clearing currentForum is fine
      // Actually, clearing messages is safer to avoid showing wrong forum data
      // MODIFIED: Don't clear if we are just navigating back but might return (keep cache)
      // But user asked "即使用户点击返回，页面也不会卸载，以便不重复读取"
      // So we should NOT clear messages here.
      
      // this.messages = [] // Keep messages in store
      // this.systemLogs = [] // Keep logs
      
      // But if we enter ANOTHER forum, we must clear.
      // fetchForum() handles clearing: `this.currentForum = null` and re-fetching.
      
      // However, we should stop thinking state?
      this.thinking = false
      this.loading = false
      
      // We only clear currentForum ref but keep data until overwritten?
      // No, if we clear currentForum, UI might break if it relies on it.
      // Let's keep currentForum too, but maybe mark as "inactive"?
      // The requirement says: "user current executing forum, page won't unload".
      // This implies keeping the state.
      
      // So leaveForum should be minimal.
    },
    
    // New Action: Clear Forum Data (explicitly called when needed, e.g. entering NEW forum)
    clearForumData() {
        this.messages = []
        this.systemLogs = []
        this.currentForum = null
        this.thinking = false
    }
  }
})
