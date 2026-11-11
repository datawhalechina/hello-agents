export const connectionEvent = 'offernote-connection'

export async function api<T>(
  path: string,
  method = 'GET',
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      signal,
      headers: body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    })
  } catch {
    window.dispatchEvent(new CustomEvent(connectionEvent, { detail: false }))
    throw new Error(
      '无法连接本地服务。请启动项目中的 start.cmd（Windows）或运行 sh start.sh（macOS / Linux），并确认页面端口与启动地址一致；连接恢复后重试。若刚提交了操作，请先确认是否已生效。',
    )
  }
  window.dispatchEvent(new CustomEvent(connectionEvent, { detail: true }))
  if (!response.ok) {
    let message = `请求未完成（${response.status}）`
    try {
      const data = await response.json()
      message = Array.isArray(data.detail)
        ? data.detail.map((e: { msg: string }) => e.msg).join('；')
        : data.detail || message
    } catch {
      /* Non-JSON errors retain their status. */
    }
    throw new Error(message)
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

export function dateLabel(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export async function streamDemonstrationAnswer(
  path: string,
  questionId: string,
  onText: (text: string) => void,
): Promise<{ question_id: string; answer: string }> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ question_id: questionId }),
    })
  } catch {
    window.dispatchEvent(new CustomEvent(connectionEvent, { detail: false }))
    throw new Error('无法连接本地服务，流式回答未完成，请检查服务后重试。')
  }
  window.dispatchEvent(new CustomEvent(connectionEvent, { detail: true }))
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(
      typeof data.detail === 'string' ? data.detail : `流式请求未完成（${response.status}）`,
    )
  }
  if (!response.body) throw new Error('浏览器未取得模型流，请重试。')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = '',
    text = ''
  try {
    while (true) {
      const chunk = await reader.read()
      buffer += decoder.decode(chunk.value, { stream: !chunk.done })
      let newline: number
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline).trimEnd()
        buffer = buffer.slice(newline + 1)
        if (!line.startsWith('data:')) continue
        const event = JSON.parse(line.slice(5).trim())
        if (event.type === 'error') throw new Error(event.message || '流式回答未完成，请重试。')
        if (event.question_id !== questionId) throw new Error('流式响应题目不一致，请重试。')
        if (event.type === 'delta' && typeof event.text === 'string') {
          text += event.text
          onText(text)
        } else if (event.type === 'done' && typeof event.answer === 'string') {
          onText(event.answer)
          return { question_id: questionId, answer: event.answer }
        }
      }
      if (chunk.done) break
    }
    throw new Error('流式连接中断，当前回答未确认保存，请重试。')
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
