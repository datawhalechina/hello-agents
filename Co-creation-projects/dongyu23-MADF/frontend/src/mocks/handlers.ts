import { http, HttpResponse } from 'msw'

export const handlers = [
  // Auth
  http.post('/api/v1/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      token_type: 'bearer'
    })
  }),

  // User
  http.get('/api/v1/users/me', () => {
    return HttpResponse.json({
      id: 1,
      username: 'testuser',
      role: 'admin'
    })
  }),

  // Personas
  http.get('/api/v1/personas', () => {
    return HttpResponse.json([
      { id: 1, name: 'Socrates', title: 'Philosopher' }
    ])
  }),

  // Simulate timeout/error
  http.get('/api/v1/error', () => {
    return new HttpResponse(null, { status: 500 })
  }),

  http.get('/api/v1/timeout', async () => {
    await new Promise(resolve => setTimeout(resolve, 5000))
    return HttpResponse.json({ message: 'delayed' })
  })
]
