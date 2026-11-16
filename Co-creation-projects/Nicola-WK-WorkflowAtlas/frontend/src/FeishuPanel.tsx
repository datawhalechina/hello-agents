import { useEffect, useState } from 'react'
import { CheckCheck, Database, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react'
import { post, request } from './api'
import './feishu.css'

interface FeishuStatus { enabled: boolean; credential_configured: boolean; mode: string; sources: { source_id: string; checkpoint: { chat_id: string; complete: boolean } }[] }
interface SyncResult { imported: number; duplicates: number; checkpoint: { complete: boolean } }

export default function FeishuPanel({ onImported }: { onImported: (sourceId?: string) => Promise<void> }) {
  const [status, setStatus] = useState<FeishuStatus | null>(null)
  const [sourceId, setSourceId] = useState('')
  const [chatId, setChatId] = useState('')
  const [incremental, setIncremental] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<SyncResult | null>(null)
  useEffect(() => { let active = true; request<FeishuStatus>('/feishu/status').then(value => { if (active) setStatus(value) }).catch(err => { if (active) setError(err instanceof Error ? err.message : String(err)) }); return () => { active = false } }, [])
  const configured = Boolean(status?.enabled && status.credential_configured)
  async function sync() {
    setBusy(true); setError(''); setResult(null)
    try {
      const value = await post<SyncResult>('/feishu/sync', { source_id: sourceId.trim(), chat_id: chatId.trim(), incremental, max_pages: 1 })
      setResult(value)
      await onImported(sourceId.trim())
      setStatus(await request<FeishuStatus>('/feishu/status'))
    } catch (err) { setError(err instanceof Error ? err.message : String(err)) } finally { setBusy(false) }
  }
  const checkpoint = status?.sources.find(source => source.source_id === sourceId)?.checkpoint
  return <section className="surface feishu-panel"><div className="panel-heading"><h3><Database size={18} /> 飞书只读同步</h3><span className={`badge ${configured ? 'accepted' : 'pending'}`}>{status ? configured ? '已配置授权' : '未配置授权' : '读取配置中'}</span></div><div className="feishu-body"><div className="feishu-description"><ShieldCheck size={21} /><div><strong>按需读取群聊历史，不发送消息</strong><p>服务端状态：{status?.enabled ? '已启用同步' : '同步未启用'} · {status?.credential_configured ? '已配置凭据' : '无访问凭据'} · {status?.mode === 'read-only' ? '只读模式' : status?.mode || '读取中'}。</p>{!configured && <p>请由部署端配置已授权的飞书访问凭据并显式启用同步。浏览器不接收或保存企业访问令牌。</p>}</div></div><div className="feishu-fields"><label>数据源标识<input placeholder="例如：feishu-product" maxLength={300} value={sourceId} disabled={!configured || busy} onChange={e => { setSourceId(e.target.value); setResult(null) }} /></label><label>飞书群 ID<input placeholder="oc_..." maxLength={300} value={chatId} disabled={!configured || busy} onChange={e => { setChatId(e.target.value); setResult(null) }} /></label></div><div className="feishu-actions"><label className="check-label"><input type="checkbox" checked={incremental} disabled={!configured || busy} onChange={e => setIncremental(e.target.checked)} /> 历史完成后进行增量同步</label><button className="button" disabled={!configured || busy || !sourceId.trim() || !chatId.trim()} onClick={sync}>{busy ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{checkpoint && !checkpoint.complete ? '继续下一页' : '同步一页消息'}</button></div>{result && <div className="success-note" role="status"><CheckCheck size={17} /><span>新增 {result.imported} 条，跳过 {result.duplicates} 条重复消息。{result.checkpoint.complete ? '当前同步窗口已完成；可勾选增量同步读取后续消息。' : '当前同步窗口尚未完成，请点击「继续下一页」。'} 导入后可点击重建工作流。</span></div>}{checkpoint && !result && <p className="muted">已有持久化断点：{checkpoint.complete ? '当前窗口完成' : '还有历史分页待同步'}，对应群 {checkpoint.chat_id}。</p>}{error && <p className="inline-error" role="alert">{error}</p>}</div></section>
}
