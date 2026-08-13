import { describe, it, expect, vi } from 'vitest'
import request from '../request'
import { server } from '../../mocks/server'
import { http, HttpResponse } from 'msw'
import { message } from 'ant-design-vue'

// Mock antd message
vi.mock('ant-design-vue', () => ({
  message: {
    error: vi.fn(),
    success: vi.fn()
  }
}))

describe('Request Utility', () => {
  it('should handle successful responses', async () => {
    const res = await request.get('/users/me')
    expect(res.status).toBe(200)
    expect(res.data.username).toBe('testuser')
  })

  it('should handle 401 Unauthorized by clearing token', async () => {
    server.use(
      http.get('/api/v1/auth-error', () => {
        return new HttpResponse(null, { status: 401 })
      })
    )
    
    localStorage.setItem('token', 'old-token')
    window.history.replaceState({}, '', '/dashboard')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      await request.get('/auth-error')
    } catch (e) {
      // Expected error
    } finally {
      consoleError.mockRestore()
    }
    expect(localStorage.getItem('token')).toBeNull()
    expect(message.error).toHaveBeenCalledWith(expect.stringContaining('会话已过期'))
  })

  it('should handle 500 Server Errors', async () => {
    server.use(
      http.get('/api/v1/server-error', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Fatal' }), { status: 500 })
      })
    )
    
    try {
      await request.get('/server-error')
    } catch (e) {
      // Expected error
    }
    expect(message.error).toHaveBeenCalledWith('服务器内部错误，请稍后重试')
  })

  it('should handle network connection failure', async () => {
    server.use(
      http.get('/api/v1/network-fail', () => {
        return HttpResponse.error()
      })
    )
    
    try {
      await request.get('/network-fail')
    } catch (e) {
      // Expected error
    }
    expect(message.error).toHaveBeenCalledWith('网络连接失败，请检查网络设置')
  })

  it('should handle general API errors with detail message', async () => {
    server.use(
      http.get('/api/v1/bad-request', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Invalid parameters' }), { status: 400 })
      })
    )
    
    try {
      await request.get('/bad-request')
    } catch (e) {
      // Expected
    }
    expect(message.error).toHaveBeenCalledWith('Invalid parameters')
  })

  it('should handle general API errors with object detail', async () => {
    server.use(
      http.get('/api/v1/bad-request-obj', () => {
        return new HttpResponse(JSON.stringify({ detail: { message: 'Object error' } }), { status: 400 })
      })
    )
    
    try {
      await request.get('/bad-request-obj')
    } catch (e) {
      // Expected
    }
    expect(message.error).toHaveBeenCalledWith('Object error')
  })

  it('should handle request configuration errors', async () => {
    // We can simulate a config error by passing invalid config to axios
    // or manually calling the interceptor error handler.
    const interceptor = (request.interceptors.response as any).handlers[0].rejected
    try {
      await interceptor({ message: 'config error' })
    } catch (e) {
      // Expected
    }
    expect(message.error).toHaveBeenCalledWith('请求配置错误')
  })

  it('should handle request interceptor errors', async () => {
    const interceptor = (request.interceptors.request as any).handlers[0].rejected
    const error = new Error('request config error')
    try {
      await interceptor(error)
    } catch (e) {
      expect(e).toBe(error)
    }
  })
})
