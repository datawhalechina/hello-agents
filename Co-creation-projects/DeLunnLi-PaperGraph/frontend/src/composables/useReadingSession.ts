import { onBeforeUnmount, onMounted } from 'vue'
import { postReadingLog, sendReadingLogOnExit } from '@/services/api'

export function useReadingSession() {
  let session: { paperId: number; startedAt: number; id: string } | null = null
  let timer: ReturnType<typeof setInterval> | undefined
  function flush(exiting = false) {
    if (!session) return
    const seconds = Math.floor((Date.now() - session.startedAt) / 1000)
    if (!Number.isFinite(seconds) || seconds < 8) return
    // Every delivery is the cumulative duration of the same idempotent session.
    const body = {
      paper_id: session.paperId, session_id: session.id,
      duration_sec: Math.min(seconds, 6 * 60 * 60), client_ts: Math.floor(session.startedAt / 1000),
    }
    if (exiting) sendReadingLogOnExit(body)
    else void postReadingLog(body).catch(() => {})
  }
  function finish() {
    flush(true)
    session = null
  }
  function start(paperId: number) {
    finish()
    session = {
      paperId, startedAt: Date.now(),
      id: globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`,
    }
  }
  const onPageHide = () => flush(true)
  const onVisibility = () => { if (document.visibilityState === 'hidden') flush(true) }
  onMounted(() => {
    timer = setInterval(() => flush(), 30_000)
    window.addEventListener('pagehide', onPageHide)
    document.addEventListener('visibilitychange', onVisibility)
  })
  onBeforeUnmount(() => {
    clearInterval(timer)
    window.removeEventListener('pagehide', onPageHide)
    document.removeEventListener('visibilitychange', onVisibility)
    finish()
  })
  return { start, finish, flush }
}
