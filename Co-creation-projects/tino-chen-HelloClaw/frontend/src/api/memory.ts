import api from './index'

export interface MemoryEntry {
  date: string
  filename: string
  content: string
  preview: string
}

export interface MemoryListResponse {
  memories: MemoryEntry[]
  total: number
}

export const memoryApi = {
  list: async () => {
    return api.get<MemoryListResponse>('/memory/list')
  },
  get: async (filename: string) => {
    return api.get<{ filename: string; date: string; content: string }>(`/memory/${filename}`)
  },
}
