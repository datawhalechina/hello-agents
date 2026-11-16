import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, LoaderCircle, RefreshCw, Trash2, X } from 'lucide-react'
import { ApiError, request } from './api'
import type { SourceDeletionPreview, SourceDeletionResult } from './types'

export default function DeleteSourceModal({ sourceId, onClose, onDeleted }: { sourceId: string; onClose: () => void; onDeleted: (result: SourceDeletionResult) => Promise<void> }) {
  const [preview, setPreview] = useState<SourceDeletionPreview | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')
  const alive = useRef(true)
  const previewSequence = useRef(0)
  const dialog = useRef<HTMLElement>(null)
  const cancelButton = useRef<HTMLButtonElement>(null)
  const loadPreview = useCallback(async () => {
    const sequence = ++previewSequence.current
    setLoading(true); setPreview(null); setConfirmation('')
    try {
      const data = await request<SourceDeletionPreview>(`/sources/delete-preview?source_id=${encodeURIComponent(sourceId)}`)
      if (alive.current && sequence === previewSequence.current) setPreview(data)
    } catch (failure) { if (alive.current && sequence === previewSequence.current) setError(failure instanceof Error ? failure.message : String(failure)) }
    finally { if (alive.current && sequence === previewSequence.current) setLoading(false) }
  }, [sourceId])
  useEffect(() => {
    alive.current = true
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    cancelButton.current?.focus()
    loadPreview()
    return () => { alive.current = false; previewSequence.current += 1; document.body.style.overflow = previousOverflow; if (previousFocus?.isConnected) previousFocus.focus() }
  }, [loadPreview])

  async function remove() {
    if (!preview || confirmation !== sourceId || deleting || loading) return
    setDeleting(true); setError('')
    try {
      const result = await request<SourceDeletionResult>(`/sources?source_id=${encodeURIComponent(sourceId)}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmation, expected_messages: preview.messages, expected_version: preview.version }) })
      await onDeleted(result)
    } catch (failure) {
      if (!alive.current) return
      if (failure instanceof ApiError && failure.status === 409) {
        await loadPreview()
        if (alive.current) setError('数据已变化或仍有处理任务。已重新读取删除范围，请等待任务完成并重新核对、输入来源标识。')
      } else setError(failure instanceof Error ? failure.message : String(failure))
    } finally { if (alive.current) setDeleting(false) }
  }

  return <div className="modal-backdrop delete-source-backdrop" onClick={() => { if (!deleting) onClose() }}>
    <section ref={dialog} className="delete-source-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-source-title" aria-describedby="delete-source-description" aria-busy={loading || deleting} onClick={event => event.stopPropagation()} onKeyDown={event => {
      if (event.key === 'Escape' && !deleting) { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const focusable = dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), [tabindex="0"]')
      if (!focusable?.length) { event.preventDefault(); return }
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }}>
      <div className="panel-heading"><h2 id="delete-source-title"><AlertTriangle size={20} /> 删除数据源</h2><button className="icon-button" disabled={deleting} onClick={onClose} aria-label="关闭删除确认"><X size={18} /></button></div>
      <div className="delete-source-body"><p id="delete-source-description">将从本地工作台移除以下数据源的消息及关联分析。请先核对影响范围，再输入完整来源标识确认。</p><div className="delete-source-name">{sourceId}</div>
        {loading ? <p className="delete-loading" role="status"><LoaderCircle size={17} className="spin" />读取删除影响范围…</p> : preview ? <>
          <dl className="delete-impact"><div><dt>原始消息</dt><dd>{preview.messages} 条</dd></div><div><dt>关联工作事实</dt><dd>{preview.facts} 条</dd></div><div><dt>失去依据的项目</dt><dd>{preview.projects_removed} 个</dd></div><div><dt>关联审核记录</dt><dd>{preview.reviews} 条</dd></div><div><dt>受影响历史快照</dt><dd>{preview.versions} 个</dd></div><div><dt>重置运行摘要</dt><dd>{preview.jobs_reset} 条</dd></div></dl>
          <div className="delete-scope-note"><p>该来源的消息、引用它的事实与审核记录会移除，历史快照中的相关内容也会清理。其他来源的原始消息及仍有依据的共享项目会保留。</p><p>{preview.checkpoint ? '此来源的飞书同步断点会一并移除。' : '此来源没有飞书同步断点。'} 全局运行摘要将重置。</p><p>原始导入文件、已有备份和飞书中的数据不在本次操作范围内。</p></div>
          <label className="delete-confirm-label">输入完整来源标识确认<input aria-label="输入完整来源标识确认删除" value={confirmation} onChange={event => setConfirmation(event.target.value)} disabled={deleting} autoComplete="off" spellCheck={false} placeholder={sourceId} maxLength={300} /></label>
        </> : <button className="button" onClick={() => { setError(''); loadPreview() }}><RefreshCw size={15} />重新读取范围</button>}
        {error && <p className="inline-error" role="alert">{error}</p>}
      </div>
      <div className="delete-source-actions"><button ref={cancelButton} className="button" disabled={deleting} onClick={onClose}>取消</button><button className="button danger-fill" disabled={loading || deleting || !preview || confirmation !== sourceId} onClick={remove}>{deleting ? <LoaderCircle className="spin" size={15} /> : <Trash2 size={15} />}{deleting ? '正在删除…' : '确认删除数据源'}</button></div>
    </section>
  </div>
}
