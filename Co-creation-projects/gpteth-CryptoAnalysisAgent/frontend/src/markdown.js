import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ gfm: true, breaks: true })

export function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ''))
}

export function formatTime(ts) {
  const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  return date.toLocaleString('zh-CN', { hour12: false })
}
