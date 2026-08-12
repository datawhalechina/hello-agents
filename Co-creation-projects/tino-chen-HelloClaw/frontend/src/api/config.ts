import api from './index'

export interface ConfigFile {
  name: string
  content: string
}

export interface ResetOptions {
  reset_sessions?: boolean
  reset_memory?: boolean
  reset_global_config?: boolean
}

export interface AgentInfo {
  name: string
}

export const configApi = {
  list: async () => {
    return api.get<{ configs: string[] }>('/config/list')
  },
  get: async (name: string) => {
    return api.get<ConfigFile>(`/config/${name}`)
  },
  update: async (name: string, content: string) => {
    return api.put<{ name: string; status: string }>(`/config/${name}`, { content })
  },
  reset: async (options: ResetOptions = {}) => {
    const params = new URLSearchParams()
    if (options.reset_sessions) params.append('reset_sessions', 'true')
    if (options.reset_memory) params.append('reset_memory', 'true')
    if (options.reset_global_config) params.append('reset_global_config', 'true')
    const query = params.toString() ? `?${params.toString()}` : ''
    return api.post<{ status: string; message: string }>(`/config/reset${query}`)
  },
  getAgentInfo: async () => {
    return api.get<AgentInfo>('/config/agent/info')
  },
}
