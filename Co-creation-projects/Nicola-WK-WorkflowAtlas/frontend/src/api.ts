export function getToken() { return sessionStorage.getItem('workflow-api-token') || '' }

export function setToken(token: string) {
  if (token) sessionStorage.setItem('workflow-api-token', token)
  else sessionStorage.removeItem('workflow-api-token')
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = 'ApiError' }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`/api${path}`, { ...init, headers })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail || response.statusText)
    if (response.status === 401) throw new ApiError(response.status, '需要访问令牌。请在左下角「连接设置」填写服务器配置的令牌。')
    throw new ApiError(response.status, detail || `请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function post<T>(path: string, body: unknown = {}) {
  return request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

export async function download(format: string, projectId?: string, sourceId?: string) {
  const params = new URLSearchParams({ format })
  if (projectId) params.set('project_id', projectId)
  if (sourceId) params.set('source_id', sourceId)
  const token = getToken()
  const response = await fetch(`/api/export?${params}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `导出失败 (${response.status})`)
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `workflow-${format}.${format === 'json' ? 'json' : 'jsonl'}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
