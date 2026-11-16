import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { post, request } from './api'
import type { Job } from './types'

export function useDiagramJob(refresh: RefObject<() => Promise<void>>, purpose: 'diagram' | 'facts' = 'diagram') {
  const [job, setJob] = useState<Job | null>(null)
  const [running, setRunning] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState('')
  const [sourceId, setSourceId] = useState('')
  const lock = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  async function start(sourceId: string) {
    if (lock.current || !sourceId) return
    setSourceId(sourceId)
    lock.current = true; setRunning(true); setJob(null); setError(''); setStopping(false)
    try {
      let result = await post<Job>(`/model/${purpose}?${new URLSearchParams({ source_id: sourceId })}`)
      if (result.source_id !== sourceId || result.purpose !== purpose) throw new Error('图谱任务与当前来源或用途不一致，请检查服务版本。')
      if (mounted.current) setJob(result)
      while (result.status === 'queued' || result.status === 'running') {
        await new Promise(resolve => setTimeout(resolve, 1000))
        if (!mounted.current) return
        try {
          const latest = await request<Job>(`/jobs/${encodeURIComponent(result.id)}`)
          if (latest.id !== result.id || latest.source_id !== sourceId || latest.purpose !== purpose) throw new Error('任务来源不一致')
          result = latest; setJob(result); setError('')
        } catch { if (mounted.current) setError('暂时无法读取图谱任务，正在重试查询；不会重新发起模型调用。') }
      }
      if (!mounted.current) return
      if (result.status === 'failed') setError(result.error || '图谱生成中断，已收到的内容会保留。')
      try { await refresh.current() } catch { if (mounted.current) setError('任务已结束，但保存结果读取失败，请刷新页面查看。') }
    } catch (failure) { if (mounted.current) setError(failure instanceof Error ? failure.message : String(failure)) }
    finally { lock.current = false; if (mounted.current) { setRunning(false); setStopping(false) } }
  }
  async function cancel() {
    if (!job || stopping || job.cancel_requested || !running) return
    setStopping(true)
    try { const result = await post<Job>(`/jobs/${encodeURIComponent(job.id)}/cancel`); if (mounted.current) setJob(result) }
    catch (failure) { if (mounted.current) { setStopping(false); setError(failure instanceof Error ? failure.message : String(failure)) } }
  }
  return { job, running, stopping, error, sourceId, start, cancel }
}
export type DiagramJobState = ReturnType<typeof useDiagramJob>
