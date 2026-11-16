import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { FileText, LoaderCircle, Network, RefreshCw } from 'lucide-react'
import { ApiError, request } from './api'
import MarkdownAnswer, { isDirectAnswer } from './MarkdownAnswer'
import FactGraphPanel from './FactGraphPanel'
import ModelProjectDiagram from './ModelProjectDiagram'
import type { DiagramJobState } from './useDiagramJob'
import type { Evidence, Message, ModelReportView, ModelWorkflowReport } from './types'

const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error)
const relations: Record<string, string> = { precedes: '先于', depends_on: '依赖', blocks: '阻塞', resolves: '解决', produces: '产生', revises: '修订', branches_to: '分支', parallel_with: '并行' }
const kinds: Record<string, string> = { task: '任务', event: '事件', decision: '决策', issue: '问题', artifact: '交付', plan: '计划' }
const timestamp = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })

function EvidenceItem({ evidence, index }: { evidence: Evidence; index: number }) {
  const [open, setOpen] = useState(false)
  const [source, setSource] = useState<Message | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!open || source) return
    const controller = new AbortController()
    setLoading(true); setError('')
    const query = new URLSearchParams({ source_id: evidence.source_id, message_id: evidence.message_id })
    request<Message>(`/evidence?${query}`, { signal: controller.signal }).then(value => {
      if (controller.signal.aborted) return
      if (value.source_id !== evidence.source_id || value.id !== evidence.message_id) throw new Error('返回的原文与证据标识不一致，请重试。')
      setSource(value)
    }).catch(failure => { if (!controller.signal.aborted) setError(messageOf(failure)) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [open, evidence.source_id, evidence.message_id, retry])
  const offset = source?.text.indexOf(evidence.quote) ?? -1
  return <details className="report-evidence-item" onToggle={event => setOpen(event.currentTarget.open)}><summary>证据 {index + 1} · {evidence.message_id}</summary><blockquote>{evidence.quote}</blockquote><small>来源：{evidence.source_id}</small>{loading && <p role="status">正在读取原始消息…</p>}{error && <div className="report-evidence-error" role="alert"><p>{error}</p><button className="button" type="button" onClick={() => setRetry(value => value + 1)}>重新读取原文</button></div>}{source && <div className="report-original-message"><div><strong>{source.sender}</strong><time>{timestamp(source.timestamp)}</time></div><p>{offset >= 0 ? <>{source.text.slice(0, offset)}<mark>{evidence.quote}</mark>{source.text.slice(offset + evidence.quote.length)}</> : source.text}</p><small>{offset >= 0 ? '原文包含此引文；模型解释仍需人工核对。' : '原文未包含此引文，请核对。'}</small></div>}</details>
}

function EvidenceCell({ evidence }: { evidence: Evidence[] }) {
  return <div className="report-evidence-list">{evidence.map((item, index) => <EvidenceItem key={`${item.source_id}/${item.message_id}/${index}`} evidence={item} index={index} />)}</div>
}

function ReportTable({ title, children, count }: { title: string; children: ReactNode; count: number }) {
  return <section className="report-table-section"><div className="report-section-heading"><h2>{title}</h2><span>{count} 条</span></div>{count ? <div className="report-table-scroll" tabIndex={0} role="region" aria-label={`${title}，可横向滚动`}>{children}</div> : <p className="report-empty-rows">报告未列出此项。</p>}</section>
}

function ReportBody({ report }: { report: ModelWorkflowReport }) {
  const workstreams = new Map(report.workstreams.map(item => [item.id, item.name]))
  const steps = new Map(report.steps.map(item => [item.id, item.title]))
  return <article className="surface model-report-document"><section className="report-summary"><h2>总览</h2><p>{report.summary}</p></section>
    <ReportTable title="项目与工作主线" count={report.workstreams.length}><table className="model-report-table"><thead><tr><th scope="col">项目 / 主线</th><th scope="col">负责人</th><th scope="col">状态</th><th scope="col">摘要</th><th scope="col">原文证据</th></tr></thead><tbody>{report.workstreams.map(item => <tr key={item.id}><th scope="row">{item.name}</th><td>{item.owners.join('、') || '未明确'}</td><td>{item.status}</td><td>{item.summary}</td><td><EvidenceCell evidence={item.evidence} /></td></tr>)}</tbody></table></ReportTable>
    <ReportTable title="工作流程" count={report.steps.length}><table className="model-report-table report-steps-table"><thead><tr><th scope="col">工作步骤</th><th scope="col">关联主线</th><th scope="col">类型</th><th scope="col">执行人</th><th scope="col">状态</th><th scope="col">时间</th><th scope="col">原文证据</th></tr></thead><tbody>{report.steps.map(item => <tr key={item.id}><th scope="row">{item.title}</th><td>{item.workstream_id ? workstreams.get(item.workstream_id) || item.workstream_id : '未明确'}</td><td>{kinds[item.kind] || item.kind}</td><td>{item.actor || '未明确'}</td><td>{item.status}</td><td>{item.occurred_at ? timestamp(item.occurred_at) : '未明确'}</td><td><EvidenceCell evidence={item.evidence} /></td></tr>)}</tbody></table></ReportTable>
    {!!report.relations.length && <ReportTable title="步骤关系" count={report.relations.length}><table className="model-report-table"><thead><tr><th scope="col">起点步骤</th><th scope="col">关系</th><th scope="col">目标步骤</th><th scope="col">模型说明</th><th scope="col">原文证据</th></tr></thead><tbody>{report.relations.map((item, index) => <tr key={index}><th scope="row">{steps.get(item.source_step_id) || item.source_step_id}</th><td>{relations[item.relation] || item.relation}</td><td>{steps.get(item.target_step_id) || item.target_step_id}</td><td>{item.rationale}</td><td><EvidenceCell evidence={item.evidence} /></td></tr>)}</tbody></table></ReportTable>}
    {report.tables.map((table, index) => <ReportTable key={index} title={table.title || `模型补充表 ${index + 1}`} count={table.rows.length}><table className="model-report-table"><thead><tr>{table.columns.map((column, i) => <th key={i} scope="col">{column}</th>)}<th scope="col">原文证据</th></tr></thead><tbody>{table.rows.map((row, i) => <tr key={i}>{table.columns.map((_, col) => <td key={col}>{row.cells[col] ?? '—'}</td>)}<td><EvidenceCell evidence={row.evidence} /></td></tr>)}</tbody></table></ReportTable>)}
    <section className="report-notes"><div><h2>待确认事项</h2>{report.uncertainties.length ? <ul>{report.uncertainties.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>模型未列出待确认事项，仍需人工核对。</p>}</div><div><h2>分析限制</h2>{report.limitations.length ? <ul>{report.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>此报告为模型解释，证据引文与实际业务情况需人工核对。</p>}</div></section>
  </article>
}

export default function ModelReportWorkspace({ sourceId, refreshToken, remote, busy, onAnalyze, onConfigure, diagramTask, onDiagram, factTask, onFacts, legacyFactCount, children }: { sourceId: string; refreshToken: number; remote: boolean; busy: boolean; onAnalyze: () => void; onConfigure: () => void; diagramTask: DiagramJobState; onDiagram: () => void; factTask: DiagramJobState; onFacts: () => void; legacyFactCount: number; children: ReactNode }) {
  const [view, setView] = useState<'report' | 'diagram' | 'legacy'>(remote ? 'diagram' : 'legacy')
  const [value, setValue] = useState<ModelReportView | null>(null)
  const [loading, setLoading] = useState(!!sourceId)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const selectedView = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(!!sourceId); setError('')
    if (!selectedView.current && remote) setView('diagram')
    if (!sourceId) { setValue(null); return () => controller.abort() }
    request<ModelReportView>(`/model/report?${new URLSearchParams({ source_id: sourceId })}`, { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return
      if (result.source_id !== sourceId) throw new Error('报告来源与当前选择不一致，请重新读取。')
      setValue(result)
      if (result.report && !selectedView.current) setView(isDirectAnswer(result.report) ? 'diagram' : 'report')
    }).catch(failure => {
      if (controller.signal.aborted) return
      setValue(null)
      setError(failure instanceof ApiError && failure.status === 404 ? '报告接口暂不可用，或当前来源不存在。请检查服务版本与所选来源；已有事实仍可在「历史事实图谱」查看。' : messageOf(failure))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [sourceId, refreshToken, remote, retry])
  const legacyContent = remote && isDirectAnswer(value?.report) && legacyFactCount === 0 ?
    <div className="surface report-guidance"><h2>此来源尚未生成结构化事实记录</h2>
      <p>已保存的模型回答与项目图谱可在上方查看。点击「生成可交互事实图谱」，即可补充项目、节点和原文依据。</p>
    </div> : children
  const factControls = remote ? <div className="page-content">
    <FactGraphPanel sourceId={sourceId} busy={busy} hasAnswer={isDirectAnswer(value?.report)}
      graph={value?.fact_graph} task={factTask} onGenerate={onFacts} />
  </div> : null
  return <><div className="report-view-tabs" role="group" aria-label="项目展示方式"><button className={view === 'report' ? 'active' : ''} aria-pressed={view === 'report'} onClick={() => { selectedView.current = true; setView('report') }}><FileText size={16} />模型回答</button><button className={view === 'diagram' ? 'active' : ''} aria-pressed={view === 'diagram'} onClick={() => { selectedView.current = true; setView('diagram') }}><Network size={16} />项目图谱</button><button className={view === 'legacy' ? 'active' : ''} aria-pressed={view === 'legacy'} onClick={() => { selectedView.current = true; setView('legacy') }}><Network size={16} />历史事实图谱</button></div>{view === 'legacy' ? <>{factControls}{legacyContent}</> : view === 'diagram' ? loading ? <div className="model-loading" role="status"><LoaderCircle size={21} className="spin" />正在读取项目图示…</div> : error ? <div className="page-content"><p className="inline-error" role="alert">{error}</p><button className="button" onClick={() => setRetry(count => count + 1)}>重新读取报告</button></div> : <ModelProjectDiagram value={value} sourceId={sourceId} busy={busy} remote={remote} task={diagramTask} onGenerate={onDiagram} onAnswer={() => { selectedView.current = true; setView('report') }} onLegacy={() => { selectedView.current = true; setView('legacy') }} /> : <div className="page-content model-report-page"><div className="section-intro"><div><h1>模型回答</h1><p>像直接聊天一样阅读模型的自然回答，表格随生成内容呈现。</p></div><button className="button primary" disabled={busy || !sourceId || !remote} onClick={onAnalyze}>{busy ? <LoaderCircle size={16} className="spin" /> : <RefreshCw size={16} />}重新生成回答</button></div>{loading ? <div className="model-loading" role="status"><LoaderCircle size={21} className="spin" />正在读取当前来源报告…</div> : error ? <div className="surface report-guidance"><p role="alert">{error}</p><button className="button" onClick={() => setRetry(count => count + 1)}>重新读取报告</button></div> : value?.report ? <><div className="report-provenance"><span><FileText size={14} />来源：{value.source_id}</span><span>{value.version !== null ? `报告版本 v${value.version}` : '已保存报告'}{value.created_at ? ` · ${timestamp(value.created_at)}` : ''}</span></div>{value.stale && <div className="report-stale" role="status"><strong>旧报告 · 来源或模型配置已变化</strong><p>下面是此前保存的报告，不代表当前来源和模型配置下的最新分析。可手动重新生成；重新调用模型可能再次计费。</p></div>}{isDirectAnswer(value.report) ? <MarkdownAnswer answer={value.report} cached={value.cached === true} /> : <><p className="report-legacy-label">历史结构化报告 · 保留原格式</p><ReportBody report={value.report} /></>}</> : <div className="surface report-guidance"><FileText size={28} /><h2>{!sourceId ? '先选择一个数据源' : '此来源尚无模型回答'}</h2><p>{!sourceId ? '在顶部选择单个来源，再生成跨消息的模型报告。' : remote ? '点击「重新生成回答」，将所选来源交给模型直接回答。生成中会显示正文；已有事实图谱仍可切换查看。' : '在「大模型设置」测试连接并明确授权后，即可为此来源生成全局报告。现有规则分析结果保留在「历史事实图谱」。'}</p>{sourceId && (remote ? <button className="button primary" disabled={busy} onClick={onAnalyze}>重新生成回答</button> : <button className="button" onClick={onConfigure}>打开大模型设置</button>)}</div>}<p className="report-review-note">回答为模型生成内容，请结合原始消息核对。图示为模型解释，不等于已核验事实或训练标签；未完整的回答也会保留，不会自动重试。</p></div>}</>
}
