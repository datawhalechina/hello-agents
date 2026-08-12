import axios from 'axios'

const API_TIMEOUT = 15000

const candidateBases = (() => {
  const envBase = import.meta.env.VITE_API_BASE_URL
  const currentHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
  const protocol = typeof window !== 'undefined' ? window.location.protocol : 'http:'

  const bases = []
  if (envBase) {
    bases.push(envBase.replace(/\/$/, ''))
  }
  bases.push('http://127.0.0.1:8000/api')
  bases.push('http://localhost:8000/api')
  bases.push(`${protocol}//${currentHost}:8000/api`)

  return [...new Set(bases)]
})()

let activeBase = null

const api = axios.create({ timeout: API_TIMEOUT })

async function resolveBase() {
  if (activeBase) {
    return activeBase
  }

  for (const base of candidateBases) {
    try {
      await axios.get(`${base}/health`, { timeout: 3000 })
      activeBase = base
      return base
    } catch (_) {
      // Try next candidate
    }
  }

  throw new Error(`No reachable backend API. Tried: ${candidateBases.join(', ')}`)
}

async function apiGet(path, config = {}) {
  const base = await resolveBase()
  return api.get(`${base}${path}`, config)
}

async function apiPost(path, body = {}, config = {}) {
  const base = await resolveBase()
  return api.post(`${base}${path}`, body, config)
}

export async function fetchSites() {
  const { data } = await apiGet('/sites')
  return data.sites
}

export async function fetchReport(siteId, startDate, endDate) {
  const { data } = await apiGet(`/reports/${siteId}`, {
    params: {
      start_date: startDate,
      end_date: endDate
    }
  })
  return data.report
}

export async function fetchRuntime() {
  const { data } = await apiGet('/runtime')
  return data.runtime
}

export async function askQuestion(question, startDate, endDate, siteId = null) {
  const { data } = await apiPost('/chat', {
    question,
    start_date: startDate,
    end_date: endDate,
    site_id: siteId
  })
  return data
}

export async function askQuestionStream(question, startDate, endDate, siteId = null, onChunk) {
  const base = await resolveBase()
  const resp = await fetch(`${base}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      question,
      start_date: startDate,
      end_date: endDate,
      site_id: siteId
    })
  })

  if (!resp.ok || !resp.body) {
    const message = await resp.text()
    throw new Error(`stream request failed: ${resp.status} ${message}`)
  }

  const meta = {
    llmEnabled: resp.headers.get('X-Agent-LLM') === 'true',
    mcpEnabled: resp.headers.get('X-Agent-MCP') === 'true',
    reportIntent: resp.headers.get('X-Agent-Report-Intent') === 'true',
    artifactUrl: resp.headers.get('X-Agent-Artifact-Url') || '',
    artifactName: resp.headers.get('X-Agent-Artifact-Name') || ''
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    onChunk(decoder.decode(value, { stream: true }), meta)
  }

  return meta
}
