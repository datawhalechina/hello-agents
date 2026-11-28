const BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // 非 JSON 错误响应，保持状态文本
    }
    throw new Error(`${response.status} ${detail}`)
  }
  return response.json()
}

function query(params) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') search.set(key, value)
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const api = {
  health: () => request('/health'),
  records: (metricType, days) => request(`/health/records${query({ metric_type: metricType, days })}`),
  trends: (metricType, days) => request(`/health/trends${query({ metric_type: metricType, days })}`),
  currentPlan: () => request('/plans/current'),
  planVersions: (planId) => request(`/plans/${encodeURIComponent(planId)}/versions`),
  trace: (traceId) => request(`/traces/${encodeURIComponent(traceId)}`),
  chatHistory: (sessionId) => request(`/chat/history${query({ session_id: sessionId })}`),
  chat: (message, sessionId) =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    }),
}
