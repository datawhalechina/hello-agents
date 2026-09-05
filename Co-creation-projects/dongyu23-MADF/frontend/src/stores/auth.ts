import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

interface User {
  id: number
  username: string
  role: string
}

interface AuthState {
  token: string | null
  user: User | null
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token'),
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    loading: false,
    error: null
  }),
  actions: {
    syncFromStorage() {
      this.token = localStorage.getItem('token')
      try {
        this.user = JSON.parse(localStorage.getItem('user') || 'null')
      } catch {
        this.user = null
        localStorage.removeItem('user')
      }
    },
    async login(form: Record<string, string>) {
      this.loading = true
      this.error = null
      try {
        const formData = new FormData()
        formData.append('username', form.username)
        formData.append('password', form.password)
        
        const res = await request.post('/auth/login', formData)
        this.token = res.data.access_token
        localStorage.setItem('token', this.token || '')
        
        const userRes = await request.get('/users/me')
        this.user = userRes.data
        localStorage.setItem('user', JSON.stringify(this.user))
        window.dispatchEvent(new Event('madf-auth-changed'))
        
        message.success('登录成功')
        // Use dynamic import to avoid circular dependency
        const router = (await import('@/router')).default
        router.push('/')
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
            const error = err as any
            this.error = error.response?.data?.detail || '登录失败，请检查用户名或密码'
        } else {
             this.error = '登录失败，请检查用户名或密码'
        }
      } finally {
        this.loading = false
      }
    },
    async register(form: Record<string, string>) {
      this.loading = true
      this.error = null
      try {
        await request.post('/auth/register', {
          username: form.username,
          email: form.email,
          password: form.password
        })
        message.success('注册成功，正在自动登录...')
        await this.login(form)
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
             const error = err as any
             this.error = error.response?.data?.detail || '注册失败，请稍后重试'
        } else {
             this.error = '注册失败，请稍后重试'
        }
      } finally {
        this.loading = false
      }
    },
    async logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event('madf-auth-changed'))
      const router = (await import('@/router')).default
      router.push('/auth/login')
      message.success('已退出登录')
    }
  }
})
