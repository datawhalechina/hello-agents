const DEFAULT_TIMEOUT_MS = 120_000

export class ApiError extends Error {
  status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })

    let payload: unknown = null
    const text = await res.text()
    if (text) {
      try {
        payload = JSON.parse(text) as unknown
      } catch {
        payload = { message: text }
      }
    }

    if (!res.ok) {
      const detail =
        payload &&
        typeof payload === 'object' &&
        'detail' in payload &&
        typeof (payload as { detail: unknown }).detail === 'string'
          ? (payload as { detail: string }).detail
          : payload &&
              typeof payload === 'object' &&
              'message' in payload &&
              typeof (payload as { message: unknown }).message === 'string'
            ? (payload as { message: string }).message
            : `请求失败（${res.status}）`
      throw new ApiError(detail, res.status)
    }

    return payload as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后重试或检查后端服务', 408)
    }
    throw new ApiError(err instanceof Error ? err.message : '网络异常', 0)
  } finally {
    window.clearTimeout(timer)
  }
}
