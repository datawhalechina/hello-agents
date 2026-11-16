import { useEffect, useRef, useState } from 'react'
import { ArrowDownToLine, CheckCheck, FileJson2, LoaderCircle, Plus, Upload } from 'lucide-react'
import { ApiError, request } from './api'
import type { ImportFormat, ImportPreview, ImportReport } from './types'

type Identity = { file: File; sourceId: string; timezone: string; format: ImportFormat }
type CheckedFile = Identity & { data: ImportPreview; content: ArrayBuffer }
const messageOf = (failure: unknown) => failure instanceof Error ? failure.message : String(failure)
const formatNames: Record<ImportFormat, string> = {
  auto: '自动识别',
  json: 'JSON',
  jsonl: 'JSONL',
  csv: 'CSV / TSV',
  txt: 'TXT',
  html: 'HTML',
}

export default function ImportPanel({ busy, onBusyChange, onImported }: { busy: boolean; onBusyChange: (value: boolean) => void; onImported: (sourceId?: string, report?: ImportReport) => Promise<void> }) {
  const [sourceId, setSourceId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [timezone, setTimezone] = useState('UTC+08:00')
  const [format, setFormat] = useState<ImportFormat>('auto')
  const [working, setWorking] = useState<'preview' | 'commit' | ''>('')
  const [checked, setChecked] = useState<CheckedFile | null>(null)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [error, setError] = useState('')
  const [needsRecheck, setNeedsRecheck] = useState(false)
  const [issuesPage, setIssuesPage] = useState(0)
  const [copyText, setCopyText] = useState('')
  const [copyNotice, setCopyNotice] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const manualReport = useRef<HTMLTextAreaElement>(null)
  const sequence = useRef(0)
  const lock = useRef(false)
  const mounted = useRef(true)
  const controller = useRef<AbortController | null>(null)
  const current = useRef({ file, sourceId, timezone, format })
  const checkedRef = useRef(checked)
  current.current = { file, sourceId, timezone, format }
  checkedRef.current = checked
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; sequence.current += 1; controller.current?.abort(); onBusyChange(false) } }, [onBusyChange])

  function reset() {
    sequence.current += 1; controller.current?.abort(); lock.current = false
    setWorking(''); onBusyChange(false); setChecked(null); setReport(null); setError(''); setNeedsRecheck(false); setIssuesPage(0); setCopyText(''); setCopyNotice('')
  }
  function isCurrent(op: number, identity: Identity) {
    return mounted.current && sequence.current === op && current.current.file === identity.file && current.current.sourceId.trim() === identity.sourceId && current.current.timezone === identity.timezone && current.current.format === identity.format
  }
  function begin(stage: 'preview' | 'commit') {
    lock.current = true; setWorking(stage); onBusyChange(true); setError(''); setReport(null)
    controller.current = new AbortController()
    return ++sequence.current
  }
  function finish(op: number) {
    if (mounted.current && sequence.current === op) { lock.current = false; setWorking(''); onBusyChange(false) }
  }
  function handleFailure(failure: unknown, op: number, identity: Identity) {
    if (!isCurrent(op, identity)) return
    if (failure instanceof ApiError && failure.status === 409) {
      setNeedsRecheck(true); setError('数据在检查后发生变化或存在冲突。请重新检查文件，再确认导入；本次未自动重试。')
    } else if (failure instanceof ApiError && failure.status === 413) setError('文件超过服务器允许的大小，请拆分后重新检查。')
    else if (failure instanceof ApiError && failure.status === 422) setError('无法检查或导入：来源标识、文件格式或时区参数无效，请核对后重试。')
    else setError(messageOf(failure))
  }
  async function commit(identity: Identity, data: ImportPreview, op: number, content: ArrayBuffer) {
    if (!isCurrent(op, identity)) return
    setWorking('commit')
    const params = new URLSearchParams({ source_id: identity.sourceId, naive_timezone: identity.timezone, format: identity.format, fingerprint: data.fingerprint })
    const result = await request<ImportReport>(`/import/commit?${params}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: content, signal: controller.current?.signal })
    if (!isCurrent(op, identity)) return
    if (result.source_id !== identity.sourceId) throw new Error('导入结果来源与当前选择不一致，请刷新来源列表核对。')
    const completedReport = {
      ...result,
      warnings: [...new Set([...data.warnings, ...result.warnings])],
    }
    setReport(completedReport)
    try { await onImported(result.source_id, completedReport) } catch { if (isCurrent(op, identity)) setError('导入已完成，但来源列表刷新失败。请刷新页面查看结果。') }
  }
  async function inspect() {
    if (lock.current || busy) return
    if (!file || !sourceId.trim()) { setError('请选择文件并填写数据源标识。'); return }
    if (file.size > 10 * 1024 * 1024) { setError('文件超过 10 MB，请拆分后导入。'); return }
    const identity = { file, sourceId: sourceId.trim(), timezone, format }
    const op = begin('preview'); setChecked(null); setNeedsRecheck(false); setIssuesPage(0); setCopyText(''); setCopyNotice('')
    try {
      const content = await file.arrayBuffer()
      if (!isCurrent(op, identity)) return
      const params = new URLSearchParams({ source_id: identity.sourceId, naive_timezone: identity.timezone, format: identity.format })
      const data = await request<ImportPreview>(`/import/preview?${params}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: content, signal: controller.current?.signal })
      if (!isCurrent(op, identity)) return
      if (data.source_id !== identity.sourceId) throw new Error('检查结果的来源与当前选择不一致，请重新检查。')
      setChecked({ ...identity, data, content })
      if (!/^[a-f0-9]{64}$/i.test(data.fingerprint || '')) { setNeedsRecheck(true); setError('检查结果缺少有效指纹，请重新检查文件后再导入。'); return }
      if (!data.issues.length && data.valid > 0) await commit(identity, data, op, content)
    } catch (failure) { handleFailure(failure, op, identity) }
    finally { finish(op) }
  }
  async function importRecognized() {
    if (lock.current || busy || !checked || needsRecheck || report || checked.data.valid <= 0) return
    const { file: checkedFile, sourceId: checkedSource, timezone: checkedTimezone, format: checkedFormat, data, content } = checked
    const identity = { file: checkedFile, sourceId: checkedSource, timezone: checkedTimezone, format: checkedFormat }
    if (current.current.file !== identity.file || current.current.sourceId.trim() !== identity.sourceId || current.current.timezone !== identity.timezone || current.current.format !== identity.format) { reset(); return }
    const op = begin('commit')
    try { await commit(identity, data, op, content) } catch (failure) { handleFailure(failure, op, identity) } finally { finish(op) }
  }
  function problemReport() {
    if (!checked?.data.issues.length) return ''
    const { data, sourceId: checkedSource, timezone: checkedTimezone, format: checkedFormat, file: checkedFile } = checked
    const payload = { source_id: checkedSource, file_name: checkedFile.name, naive_timezone: checkedTimezone, format: checkedFormat, format_detected: data.format_detected, total: data.total, valid: data.valid, imported_candidates: data.imported_candidates, duplicates: data.duplicates, issues: data.issues, warnings: data.warnings }
    return JSON.stringify(payload, null, 2)
  }
  function downloadIssues() {
    const text = problemReport()
    if (!text || !checked) return
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `${checked.sourceId.replace(/[^\p{L}\p{N}._-]/gu, '_').slice(0, 100) || 'import'}-import-issues.json`
    document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  async function copyIssues() {
    const text = problemReport()
    const snapshot = checked
    const op = sequence.current
    if (!text || !snapshot) return
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(text)
      if (mounted.current && sequence.current === op && checkedRef.current === snapshot) { setCopyText(''); setCopyNotice('问题报告已复制到剪贴板。') }
    } catch {
      if (mounted.current && sequence.current === op && checkedRef.current === snapshot) { setCopyText(text); setCopyNotice('浏览器未允许直接复制。请使用下方纯文本报告，选中后按 Ctrl+C。') }
    }
  }

  const preview = checked?.data
  const badRecords = preview ? new Set(preview.issues.filter(issue => issue.position > 0).map(issue => issue.position)).size : 0
  const fileIssues = preview?.issues.some(issue => issue.position === 0)
  const disabled = !!working || busy
  const configurationDisabled = working === 'commit' || busy
  return <section className="surface import-surface"><h2><Upload size={18} />导入聊天导出</h2><p className="muted">直接选择飞书、微信、QQ 等常见文本导出。先检查文件，全部通过后完成导入；有异常时由你选择是否导入有效消息。</p>
    <label>数据源标识<input placeholder="例如：product-team-2026" value={sourceId} disabled={configurationDisabled} onChange={event => { reset(); setSourceId(event.target.value) }} maxLength={300} /></label>
    <label>文件格式<select value={format} disabled={configurationDisabled} onChange={event => { reset(); setFormat(event.target.value as ImportFormat) }}><option value="auto">自动识别（推荐）</option><option value="json">JSON</option><option value="jsonl">JSONL</option><option value="csv">CSV / TSV</option><option value="txt">TXT</option><option value="html">HTML</option></select></label>
    <label>原始时间未带时区时<select value={timezone} disabled={configurationDisabled} onChange={event => { reset(); setTimezone(event.target.value) }}><option value="UTC+08:00">北京时间（UTC+8）</option><option value="UTC">UTC（UTC+0）</option></select></label><p className="muted">没有时区的原始时间采用所选时区；已有时区或时间戳保持不变。</p>
    <button className={`dropzone ${file ? 'has-file' : ''}`} disabled={configurationDisabled} onClick={() => { if (input.current) { input.current.value = ''; input.current.click() } }}><FileJson2 size={28} /><strong>{file?.name || '选择消息文件'}</strong><span>{file ? `${(file.size / 1024).toFixed(1)} KB` : 'JSON / JSONL / CSV / TSV / TXT / HTML，最大 10 MB'}</span></button><input ref={input} type="file" accept=".json,.jsonl,.csv,.tsv,.txt,.html,.htm,application/json,text/plain,text/csv,text/tab-separated-values,text/html" aria-label="选择消息文件" hidden disabled={configurationDisabled} onChange={event => { reset(); setFile(event.target.files?.[0] || null) }} />
    <button className="button primary full" onClick={inspect} disabled={disabled || !file || !sourceId.trim()}>{working ? <LoaderCircle size={16} className="spin" /> : <Plus size={16} />}{working === 'preview' ? '正在检查文件…' : working === 'commit' ? '正在导入消息…' : needsRecheck || report ? '重新检查并导入' : '检查并导入消息'}</button>
    {preview && <section className="import-preview" aria-label="导入预检结果"><div className="import-preview-heading"><h3>文件检查结果</h3><span>识别格式 {formatNames[preview.format_detected] || preview.format_detected}</span></div><p className={`import-preview-state ${preview.issues.length ? 'has-issues' : ''}`} role="status">{report ? preview.issues.length ? '已按你的选择导入可识别消息；异常记录未写入。' : '检查通过，已完成导入。' : working === 'commit' ? preview.issues.length ? '正在按你的选择保存可识别消息，异常记录不写入…' : '检查通过，正在保存可识别消息…' : '仅完成检查，尚未导入任何消息。'}</p><dl className="import-preview-counts">{[{ label: '总记录', value: preview.total }, { label: '可识别', value: preview.valid }, { label: '预计新增', value: preview.imported_candidates }, { label: '重复', value: preview.duplicates }, { label: '异常记录', value: fileIssues && !badRecords ? '文件级错误' : badRecords }].map(item => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl><p className="import-preview-help">可识别数按唯一消息计，重复数按原始重复记录计；同一条异常记录可能有多个问题。</p>
      {!!preview.issues.length && <><div className="import-issues-scroll" role="region" tabIndex={0} aria-label="全部导入异常，可横向滚动"><table><thead><tr><th scope="col">位置</th><th scope="col">行号</th><th scope="col">字段</th><th scope="col">原因</th></tr></thead><tbody>{preview.issues.slice(issuesPage * 100, issuesPage * 100 + 100).map((issue, index) => <tr key={index}><td>{issue.position === 0 ? '整份文件' : `第 ${issue.position} 条`}</td><td>{issue.line ?? '—'}</td><td>{issue.field || '—'}</td><td>{issue.detail}</td></tr>)}</tbody></table></div>{preview.issues.length > 100 && <div className="import-issues-pagination"><span>第 {issuesPage * 100 + 1}–{Math.min((issuesPage + 1) * 100, preview.issues.length)} 项，共 {preview.issues.length} 项诊断</span><div><button className="button" disabled={issuesPage === 0} onClick={() => setIssuesPage(value => value - 1)}>上一页</button><button className="button" disabled={(issuesPage + 1) * 100 >= preview.issues.length} onClick={() => setIssuesPage(value => value + 1)}>下一页</button></div></div>}<p className="import-preview-help">{preview.issues.length > 100 ? '每页显示 100 项，可翻页查看或下载完整错误记录。' : ''}页面仅展示问题原因。下载的错误文件包含原始异常记录，请妥善保管。</p><div className="import-preview-actions"><button className="button" onClick={downloadIssues} disabled={!!working}><ArrowDownToLine size={15} />下载错误记录</button><button className="button" disabled={!!working} onClick={copyIssues}>复制问题报告</button>{preview.valid > 0 && !report && <button className="button primary" disabled={disabled || needsRecheck} onClick={importRecognized}>仅导入可识别的 {preview.valid} 条</button>}</div>{copyNotice && <p className="import-preview-help" role="status">{copyNotice}</p>}{copyText && <div className="import-report-backup"><label>问题报告（仅本次查看）<textarea ref={manualReport} aria-label="问题报告原始 JSON" readOnly value={copyText} rows={7} /></label><button className="button" onClick={() => { manualReport.current?.focus(); manualReport.current?.select() }}>选中问题报告文本</button></div>}{preview.valid > 0 && !report && <p className="import-preview-help">仅导入你确认的可识别消息；异常记录不写入，已存在的相同消息自动跳过。</p>}</>}
      {!!preview.warnings.length && <ul className="import-preview-warnings">{preview.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
    </section>}
    {report && <div className="success-note" role="status"><CheckCheck size={17} />实际新增 {report.imported} 条，已有 {report.duplicates} 条。{report.warnings.join('；')}</div>}{report && preview && preview.duplicates > 0 && <p className="import-local-note">保存结果按去重后的可识别消息计；预检重复数按原始记录计，两者不相加。</p>}{error && <p className="inline-error" role="alert">{error}</p>}<p className="import-local-note">检查和导入不调用大模型，不覆盖已存历史消息。需要分析时，再手动启动。</p>
    <details className="format-help"><summary>支持的导出格式</summary><p>支持常见聊天 JSON / JSONL、带列名的 CSV / TSV、多行 TXT 和静态 HTML 文本导出，以及 ChatLab、WeChatMsg 等常见导出结构。保留原文件内容，选择文件后即可检查；自动识别不匹配时，可手动指定文件格式。</p><p>检查结果会列出无法识别的记录及转换提醒，例如缺少平台消息 ID 时派生的本地 ID。</p></details>
  </section>
}
