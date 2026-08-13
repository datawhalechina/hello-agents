import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'

describe('auth storage synchronization', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('refreshes token and user from another tab storage update', () => {
    const store = useAuthStore()
    localStorage.setItem('token', 'new-token')
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'owner', role: 'user' }))

    store.syncFromStorage()

    expect(store.token).toBe('new-token')
    expect(store.user?.username).toBe('owner')
  })

  it('clears in-memory auth after storage logout', () => {
    localStorage.setItem('token', 'old-token')
    const store = useAuthStore()
    localStorage.clear()

    store.syncFromStorage()

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })
})
