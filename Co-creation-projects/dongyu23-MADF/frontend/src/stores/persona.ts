import { defineStore } from 'pinia'
import request from '@/utils/request'

export interface Persona {
  id: number
  owner_id: number
  name: string
  title: string
  bio: string
  theories: string[]
  stance: string
  system_prompt: string
  is_public: boolean
}

interface CreatePersonaData {
    name: string;
    title?: string;
    bio?: string;
    theories?: string[];
    stance?: string;
    system_prompt?: string;
    is_public?: boolean;
}

export const usePersonaStore = defineStore('persona', {
  state: () => ({
    personas: [] as Persona[],
    loading: false
  }),
  actions: {
    async fetchPersonas(ownerId?: number) {
      this.loading = true
      try {
        const params = { ...(ownerId ? { owner_id: ownerId } : {}), limit: 500 }
        const res = await request.get('/personas/', { params })
        this.personas = res.data
      } catch (error) {
        console.error('Failed to fetch personas:', error)
        this.personas = []
      } finally {
        this.loading = false
      }
    },
    async createPersona(data: CreatePersonaData) {
      this.loading = true
      try {
        const res = await request.post('/personas/', data)
        // Optimistic update: Add to list immediately
        this.personas.unshift(res.data)
      } catch (error) {
        console.error('Failed to create persona:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async createPresetPersonas() {
      try {
        await request.post('/personas/batch/preset')
        await this.fetchPersonas()
      } catch (error) {
        console.error('Failed to create preset personas:', error)
        throw error
      }
    },
    async updatePersona(id: number, data: Partial<CreatePersonaData>) {
      // Snapshot
      const index = this.personas.findIndex(p => p.id === id)
      const previousPersona = index !== -1 ? { ...this.personas[index] } : null
      
      // Optimistic update
      if (index !== -1) {
          this.personas[index] = { ...this.personas[index], ...data } as Persona
      }
      
      try {
        const res = await request.put(`/personas/${id}`, data)
        // Update with server response to ensure consistency
        if (index !== -1) {
            this.personas[index] = res.data
        }
      } catch (error) {
        console.error('Failed to update persona:', error)
        // Rollback
        if (previousPersona && index !== -1) {
            this.personas[index] = previousPersona
        }
        throw error
      }
    },
    async deletePersona(id: number) {
      // Snapshot
      const previousPersonas = [...this.personas]
      
      // Optimistic update
      this.personas = this.personas.filter(p => p.id !== id)
      
      try {
        await request.delete(`/personas/${id}`)
      } catch (error) {
        console.error('Failed to delete persona:', error)
        // Rollback
        this.personas = previousPersonas
        throw error
      }
    }
  }
})
