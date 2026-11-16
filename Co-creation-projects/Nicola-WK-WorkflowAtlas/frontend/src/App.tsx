import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowDownToLine, ArrowRight, Check, CheckCheck, ChevronDown, ChevronRight, CircleHelp, Clock3, Cpu, Database, FileJson2, FileText, Filter, GitBranch, Layers3, ListChecks, LoaderCircle, Network, Play, RefreshCw, Search, Settings2, ShieldCheck, Trash2, Upload, Workflow as WorkflowIcon, X } from 'lucide-react'
import { download, getToken, post, request, setToken } from './api'
import FeishuPanel from './FeishuPanel'
import SourceQuality from './SourceQuality'
import DeleteSourceModal from './DeleteSourceModal'
import ModelSettingsPage from './ModelSettingsPage'
import ModelReportWorkspace from './ModelReportWorkspace'
import MarkdownAnswer from './MarkdownAnswer'
import ImportPanel from './ImportPanel'
import { useDiagramJob } from './useDiagramJob'
import { AttributionDetails, EvidenceQuote } from './EvidenceDetails'
import type { Audit, Fact, FactKind, ImportReport, Job, Message, Project, ReviewStatus, Runtime, Source, SourceAnalysis, SourceDeletionResult, Stats, Version, Workflow, WorkflowEdge } from './types'

type Page = 'projects' | 'sources' | 'review' | 'runtime' | 'exports' | 'model'
const kinds: Record<FactKind, string> = { task: '任务', event: '事件', decision: '决策', issue: '问题', artifact: '交付', plan: '计划' }
const relations: Record<string, string> = { precedes: '时间先后', depends_on: '依赖', blocks: '阻塞', resolves: '解决', produces: '交付', revises: '返工', branches_to: '分支', parallel_with: '并行' }
const reviewNames: Record<ReviewStatus, string> = { pending: '待审核', accepted: '已采纳', rejected: '已驳回' }
const sourceTypeNames: Record<string, string> = {
  feishu: '飞书消息',
  wechat: '微信消息',
  qq: 'QQ 消息',
  chat: '通用聊天',
  document: '文档',
  json: '本地导入',
}
const stages: Record<string, string> = { 'Information Filter': '工作信息筛选', 'Fact Extractor': '原子事实提取', 'Project Resolver': '项目与实体关联', 'Relation Reasoner': '关系推断', 'Workflow Reconstructor': '工作流重建', 'Evidence Verifier': '原始证据核验' }
const date = (value: string, time = true) => new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', ...(time ? { hour: '2-digit', minute: '2-digit' } : {}) })
const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error)
const withSource = (path: string, sourceId: string) => { const [base, search = ''] = path.split('?'); const params = new URLSearchParams(search); if (sourceId) params.set('source_id', sourceId); const query = params.toString(); return base + (query ? `?${query}` : '') }
const nav = [
  { id: 'projects' as const, label: '项目工作流', icon: Network },
  { id: 'sources' as const, label: '数据源', icon: Database },
  { id: 'review' as const, label: '事实审核', icon: ListChecks },
  { id: 'runtime' as const, label: 'Agent 运行', icon: Activity },
  { id: 'model' as const, label: '大模型设置', icon: Cpu },
  { id: 'exports' as const, label: '数据导出', icon: ArrowDownToLine },
]

function Empty({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return <div className="empty"><div className="empty-icon"><WorkflowIcon size={30} /></div><h2>{title}</h2><p>{children}</p>{action}</div>
}

function Badge({ fact }: { fact: Fact }) { return <span className={`badge ${fact.review_status}`}>{reviewNames[fact.review_status]}</span> }

function Graph({ graph, selectedId, onSelect }: { graph: Workflow; selectedId?: string; onSelect: (fact: Fact) => void }) {
  const [showTemporal, setShowTemporal] = useState(true)
  const nodes = [...graph.nodes, ...(graph.related_nodes || [])].sort((a, b) => Date.parse(a.occurred_at) - Date.parse(b.occurred_at))
  const factsById = new Map([...graph.facts, ...(graph.related_facts || [])].map(fact => [fact.id, fact]))
  const nodesById = new Map(nodes.map(node => [node.id, node]))
  const positions = new Map(nodes.map((node, i) => [node.id, { x: 30 + (i % 3) * 310, y: 55 + Math.floor(i / 3) * 178 }]))
  const edges = [...graph.edges, ...(graph.related_edges || [])].filter(edge => showTemporal || edge.relation !== 'precedes')
  const selectedNode = nodes.find(node => node.fact_ids.includes(selectedId || ''))
  const nodeFact = (id: string) => nodesById.get(id)?.fact_ids.map(key => factsById.get(key)).find(Boolean)
  const path = (edge: WorkflowEdge) => {
    const a = positions.get(edge.source), b = positions.get(edge.target)
    if (!a || !b) return null
    if (a.y === b.y && a.x < b.x) return { d: `M ${a.x + 254} ${a.y + 52} C ${a.x + 280} ${a.y + 52}, ${b.x - 22} ${b.y + 52}, ${b.x - 4} ${b.y + 52}`, tx: (a.x + b.x + 254) / 2, ty: a.y + 40 }
    if (a.y === b.y) return { d: `M ${a.x + 128} ${a.y} C ${a.x + 128} ${a.y - 48}, ${b.x + 128} ${b.y - 48}, ${b.x + 128} ${b.y - 4}`, tx: (a.x + b.x) / 2 + 128, ty: a.y - 28 }
    const down = b.y > a.y
    const y1 = a.y + (down ? 104 : 0), y2 = b.y + (down ? -4 : 108)
    return { d: `M ${a.x + 128} ${y1} C ${a.x + 128} ${(y1 + y2) / 2}, ${b.x + 128} ${(y1 + y2) / 2}, ${b.x + 128} ${y2}`, tx: (a.x + b.x) / 2 + 128, ty: (y1 + y2) / 2 - 7 }
  }
  return <>
    <div className="graph-tools"><span><span className="legend-dot" /> 显式工作关系 <span className="legend-line" /> 时间先后</span><label className="check-label"><input type="checkbox" checked={showTemporal} onChange={e => setShowTemporal(e.target.checked)} /> 显示时序线</label></div>
    {!!graph.related_nodes?.length && <p className="graph-related-note">关联项目：{[...new Set(graph.related_facts?.map(fact => fact.project_hint).filter(Boolean))].join('、')}</p>}
    <div className="graph-viewport" role="region" tabIndex={0} aria-label="工作流图谱，可横向滚动">
      <svg className="workflow-svg" viewBox={`0 0 950 ${Math.max(300, Math.ceil(nodes.length / 3) * 178 + 40)}`} role="group" aria-label={`${graph.project.name}工作流图谱`}>
        <defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.8" fill="#dbe2ed" /></pattern><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#6e849f" /></marker><marker id="arrow-work" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#258c80" /></marker></defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        {edges.map(edge => { const p = path(edge); if (!p) return null; const explicit = edge.relation !== 'precedes'; const focused = edge.source === selectedNode?.id || edge.target === selectedNode?.id; return <g key={edge.id} ><title>{relations[edge.relation] || edge.relation}：{edge.rationale}</title><path d={p.d} fill="none" stroke={explicit ? '#258c80' : '#6e849f'} strokeWidth={focused ? 2.7 : explicit ? 2 : 1.3} strokeDasharray={explicit ? undefined : '4 4'} markerEnd={`url(#${explicit ? 'arrow-work' : 'arrow'})`} />{explicit && <><rect x={p.tx - 23} y={p.ty - 11} width="46" height="18" rx="4" fill="#f5faf9" /><text x={p.tx} y={p.ty + 1} textAnchor="middle" className="edge-label">{relations[edge.relation]}</text></>}</g> })}
        {nodes.map(node => { const p = positions.get(node.id)!; const fact = nodeFact(node.id); const selected = node.id === selectedNode?.id; const related = node.project_id !== graph.project.id; const label = node.label.replace(/【[^】]+】/g, '').trim(); const lines = label.match(/.{1,19}/gu) || [label]; return <g key={node.id} className={`graph-node ${selected ? 'selected' : ''} ${related ? 'related-node' : ''}`}  transform={`translate(${p.x},${p.y})`} role="button" tabIndex={0} aria-label={`${kinds[node.kind]}：${node.label}`} aria-pressed={selected} onClick={() => fact && onSelect(fact)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); if (fact) onSelect(fact) } }}><title>{related ? `${fact?.project_hint || '关联项目'} · ${node.label}` : node.label}</title><rect className="node-body" width="254" height="104" rx="9" /><rect className={`node-color ${node.kind}`} width="4" height="78" y="13" rx="2" /><text className={`node-kind ${node.kind}`} x="18" y="24">{related ? '关联项目 · ' : ''}{kinds[node.kind]}</text><text className="node-time" x="236" y="24" textAnchor="end">{date(node.occurred_at, false)}</text>{lines.slice(0, 2).map((line, i) => <text key={i} className="node-title" x="18" y={48 + i * 20}>{line}{i === 1 && lines.length > 2 ? '…' : ''}</text>)}<circle cx="22" cy="88" r="3" fill={fact?.review_status === 'accepted' ? '#188779' : '#c38a2b'} /><text className="node-review" x="31" y="92">{fact ? reviewNames[fact.review_status] : node.status}</text><text className="node-count" x="236" y="92" textAnchor="end">{node.evidence.length} 条证据</text></g> })}
      </svg>
      {!nodes.length && <Empty title="没有可展示的图谱节点">当前项目尚无通过证据核验的节点，请查看事实审核。</Empty>}
    </div>
    <div className="graph-foot"><CircleHelp size={14} /> 时序线仅表示发生顺序，不代表因果。选择节点查看原始证据。</div>
  </>
}

function Timeline({ facts, selectedId, onSelect }: { facts: Fact[]; selectedId?: string; onSelect: (fact: Fact) => void }) {
  return <div className="timeline">{facts.map(fact => <button className={`timeline-entry ${selectedId === fact.id ? 'selected' : ''}`} key={fact.id} onClick={() => onSelect(fact)}><span className="timeline-date">{date(fact.occurred_at)}</span><span className={`timeline-dot ${fact.kind}`} /><span className="timeline-content"><span className={`kind ${fact.kind}`}>{kinds[fact.kind]}</span><strong>{fact.summary}</strong><span className="timeline-meta">{fact.actor || '未标明负责人'} <span>{fact.evidence.length} 条原始证据</span></span></span><Badge fact={fact} /><ChevronRight size={16} /></button>)}{!facts.length && <Empty title="暂无事实">导入消息并重建工作流后，事实会按时间排列。</Empty>}</div>
}

function EvidencePanel({ fact, historical, onReviewed, onClose }: { fact: Fact | null; historical: boolean; onReviewed: (fact: Fact) => void; onClose: () => void }) {
  const [messages, setMessages] = useState<(Message | null)[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [reviewer, setReviewer] = useState('')
  const [note, setNote] = useState('')
  useEffect(() => {
    let active = true
    setMessages([]); setError(''); setNote('')
    if (fact) {
      setLoading(true)
      Promise.all(fact.evidence.map(e => request<Message>(`/evidence?source_id=${encodeURIComponent(e.source_id)}&message_id=${encodeURIComponent(e.message_id)}`))).then(items => { if (active) setMessages(items) }).catch(err => { if (active) setError(messageOf(err)) }).finally(() => { if (active) setLoading(false) })
    }
    return () => { active = false }
  }, [fact?.id])
  async function review(status: ReviewStatus) {
    if (!fact || !reviewer.trim()) { setError('请填写审核人姓名。'); return }
    setSaving(true); setError('')
    try { const result = await post<Fact>(`/facts/${encodeURIComponent(fact.id)}/review`, { status, reviewer: reviewer.trim(), note }); onReviewed(result) } catch (err) { setError(messageOf(err)) } finally { setSaving(false) }
  }
  return <aside className={`evidence-panel ${fact ? 'has-selection' : ''}`} aria-label="证据与审核"><div className="panel-heading"><h2><FileText size={17} /> 证据与审核</h2>{fact && <button className="icon-button" onClick={onClose} aria-label="关闭证据"><X size={16} /></button>}</div>{fact ? <div className="inspector-body"><div className="inspector-title"><span className={`kind ${fact.kind}`}>{kinds[fact.kind]}</span><Badge fact={fact} /><h3>{fact.summary}</h3><div className={`verification ${fact.verified ? 'verified' : 'unverified'}`}><ShieldCheck size={16} />{fact.verified ? '来源引文已核验' : '原始证据尚未通过核验'}</div></div><dl className="fact-details"><div><dt>{fact.attributes.time_is_evidence_time === true ? '消息时间（业务时间未明确）' : '发生时间'}</dt><dd>{date(fact.occurred_at)}</dd></div><div><dt>事实状态</dt><dd>{fact.status}</dd></div><div><dt>提取置信度</dt><dd>{Math.round(fact.confidence * 100)}% <span>需人工判断</span></dd></div></dl><AttributionDetails fact={fact} /><div className="source-title">原始证据 <span>{fact.evidence.length}</span></div>{loading && <p className="muted loading-inline"><LoaderCircle className="spin" size={16} /> 读取原始消息…</p>}{fact.evidence.map((evidence, index) => <EvidenceQuote key={`${evidence.source_id}/${evidence.message_id}/${index}`} fact={fact} evidence={evidence} source={messages[index]} index={index} />)}<div className="review-section"><h3>人工审核</h3>{historical ? <p className="note">正在查看历史快照。切换到「最新版本」后可提交审核。</p> : <><p className="muted">确认事实与原文一致后采纳，审核会写入记录。</p><label>审核人<input value={reviewer} onChange={event => setReviewer(event.target.value)} placeholder="填写姓名" autoComplete="name" maxLength={100} /></label><label>审核备注<textarea value={note} onChange={event => setNote(event.target.value)} placeholder="补充判断依据（选填）" rows={2} maxLength={4000} /></label><div className="review-actions"><button className="button primary" disabled={saving || !fact.verified} onClick={() => review('accepted')}><Check size={15} /> 采纳事实</button><button className="button" disabled={saving} onClick={() => review('rejected')}>驳回</button>{fact.review_status !== 'pending' && <button className="text-button" disabled={saving} onClick={() => review('pending')}>重置</button>}</div></>}{error && <p className="inline-error" role="alert">{error}</p>}</div></div> : <div className="inspector-empty"><div className="outline-document"><FileText size={36} /><Check size={17} /></div><h3>让每个事实都有来处</h3><p>选择一个节点或时间线事件，查看支撑它的原始消息并进行审核。</p><div className="evidence-principle"><ShieldCheck size={15} /> 证据核验与人工采纳分别记录</div></div>}</aside>
}

function SourcePage({ sources, busy, onProcess, onImported, onDeleted }: { sources: Source[]; busy: boolean; onProcess: () => void; onImported: (sourceId?: string, report?: ImportReport) => Promise<void>; onDeleted: (result: SourceDeletionResult) => Promise<void> }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [selectedSource, setSelectedSource] = useState('')
  const [deletingSource, setDeletingSource] = useState<string | null>(null)
  useEffect(() => { let active = true; if (selectedSource) request<Message[]>(`/messages?source_id=${encodeURIComponent(selectedSource)}&limit=50`).then(items => { if (active) setMessages(items) }).catch(err => { if (active) setError(messageOf(err)) }); return () => { active = false } }, [selectedSource])
  useEffect(() => { if (selectedSource && !sources.some(source => source.id === selectedSource)) { setSelectedSource(''); setMessages([]) } }, [sources, selectedSource])
  return <div className="page-content"><div className="section-intro"><div><h1>数据源</h1><p>导入历史消息，保留原始内容与来源。重复导入会自动去重。</p></div><button className="button primary" onClick={onProcess} disabled={busy || !sources.length}><RefreshCw size={16} className={busy ? 'spin' : ''} /> 重建工作流</button></div><div className="source-layout"><ImportPanel busy={busy} onBusyChange={setUploading} onImported={onImported} /><section className="surface source-list"><div className="panel-heading"><h2>已连接来源</h2><span className="count">{sources.length}</span></div>{sources.length ? sources.map(source => <div className="source-entry" key={source.id}><button className={`source-row ${selectedSource === source.id ? 'selected' : ''}`} onClick={() => setSelectedSource(source.id)}><span className="source-icon"><Database size={19} /></span><span><strong>{source.id}</strong><span>{sourceTypeNames[source.type] || '本地导入'} · 最近 {date(source.last_timestamp)}</span></span><b>{source.message_count}<small>条消息</small></b><ChevronRight size={17} /></button><div className="source-entry-actions"><button className="button danger-outline" aria-label={`删除数据源 ${source.id}`} disabled={busy || uploading} onClick={() => setDeletingSource(source.id)}><Trash2 size={15} />删除</button></div></div>) : <Empty title="还没有导入数据">选择本地文件，或使用顶部的模拟数据体验完整流程。</Empty>}<div className="note source-note"><ShieldCheck size={16} /> 飞书接入仅支持只读历史与增量同步；真实授权由部署端配置。</div></section></div>{error && <p className="inline-error" role="alert">{error}</p>}<FeishuPanel onImported={onImported} />{selectedSource && <section className="surface messages-section"><div className="panel-heading"><h2>{selectedSource} 的原始消息</h2><span className="muted">最多展示 50 条原始消息</span></div>{messages.map(message => <article className="raw-message" key={`${message.source_id}/${message.id}`}><div><strong>{message.sender}</strong><time>{date(message.timestamp)}</time></div><p>{message.text}</p><small>{message.id}</small></article>)}</section>}{deletingSource !== null && <DeleteSourceModal sourceId={deletingSource} onClose={() => setDeletingSource(null)} onDeleted={async result => { setDeletingSource(null); if (selectedSource === result.source_id) { setSelectedSource(''); setMessages([]) } await onDeleted(result) }} />}</div>
}

function RuntimePage({ runtime }: { runtime: Runtime | null }) {
  const results = runtime?.agent_results || []
  return <div className="page-content"><div className="section-intro"><div><h1>Agent 运行</h1><p>主 Agent 按阶段调度六个专用角色，合并结构化结果并核验来源。</p></div><span className="mode-pill"><span /> {runtime?.provider === 'local-demo' ? '本地规则演示' : runtime?.provider || '读取中'}</span></div><div className="runtime-banner"><WorkflowIcon size={27} /><div><strong>Workflow Orchestrator</strong><p>HelloAgents {runtime?.framework || '—'} · 每个阶段使用有限上下文</p></div><span className="badge accepted">{results.length ? '已完成分析' : '等待处理任务'}</span></div><div className="stage-list">{(runtime?.agents || Object.keys(stages)).map((agent, i) => { const result = results.find(item => item.agent === agent); return <section className="stage" key={agent}><span className="stage-number">{i + 1}</span><div className="stage-title"><h2>{stages[agent] || agent}</h2><span>{agent}</span></div><div className="stage-detail"><p>{result?.detail || '导入数据并重建工作流后，显示此阶段的实际执行结果。'}</p>{result && <span>输入 {result.input_count} · 输出 {result.output_count} · {result.duration_ms.toFixed(1)} ms</span>}</div><span className={`stage-status ${result?.status || ''}`}>{result?.status === 'completed' ? <><Check size={15} /> 完成</> : result?.status === 'failed' ? '失败' : result?.status === 'skipped' ? '跳过' : '未运行'}</span></section> })}</div><div className="note runtime-note"><ShieldCheck size={19} /><div><strong>当前运行边界</strong><p>{runtime?.provider === 'local-demo' ? '本地演示采用确定性规则与显式项目、实体标记。它展示可追溯的处理闭环，不能替代复杂自然语言场景下的模型评估。' : '外部模型分析需要服务端显式启用并获得数据传输授权。'} 飞书真实数据与外部模型调用均需单独授权。</p></div></div></div>
}

function ExportPage({ projects, facts, onExport }: { projects: Project[]; facts: Fact[]; onExport: (format: string, project?: string) => void }) {
  const [project, setProject] = useState('')
  const accepted = facts.filter(fact => fact.verified && fact.review_status === 'accepted' && (!project || fact.project_id === project)).length
  return <div className="page-content"><div className="section-intro"><div><h1>数据导出</h1><p>将重建结果带到分析工具或下游训练流程，来源引用与审核状态随数据保留。</p></div><label className="inline-label">导出范围<select value={project} onChange={e => setProject(e.target.value)}><option value="">全部项目与未归属事实</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label></div><div className="export-options">{[{ format: 'json', title: '完整工作流', tag: 'JSON', icon: Network, text: '项目、事实、节点和关系的完整结构，附原始证据引用及重建警告。', action: '导出 JSON' }, { format: 'jsonl', title: '结构化事实', tag: 'JSONL', icon: FileJson2, text: '逐行导出工作事实，便于数据分析、批量处理及其他系统接入。', action: '导出 JSONL' }, { format: 'training', title: '已审核训练数据', tag: 'JSONL', icon: ShieldCheck, text: `当前范围 ${accepted} 条事实通过证据核验并经人工采纳。其他事实不会被标记为可信训练标签。`, action: '导出训练数据' }].map(item => <section className="surface export-option" key={item.format}><div className="export-icon"><item.icon size={27} /></div><span className="file-tag">{item.tag}</span><h2>{item.title}</h2><p>{item.text}</p><button className="button" onClick={() => onExport(item.format, project || undefined)}><ArrowDownToLine size={16} />{item.action}</button></section>)}</div><div className="note"><CircleHelp size={17} /> 导出不会改变审核状态。尚无采纳事实时，训练数据文件为空。</div></div>
}

export default function App() {
  const [page, setPage] = useState<Page>('projects')
  const [sourceId, setSourceId] = useState(() => new URLSearchParams(window.location.search).get('source') || '')
  const [sourceAnalysis, setSourceAnalysis] = useState<SourceAnalysis | null>(null)
  const [onlyUnassigned, setOnlyUnassigned] = useState(false)
  const refreshSequence = useRef(0)
  const graphSequence = useRef(0)
  const [stats, setStats] = useState<Stats | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [facts, setFacts] = useState<Fact[]>([])
  const [runtime, setRuntime] = useState<Runtime | null>(null)
  const [projectId, setProjectId] = useState('')
  const [graph, setGraph] = useState<Workflow | null>(null)
  const [versions, setVersions] = useState<Version[]>([])
  const [version, setVersion] = useState('')
  const [view, setView] = useState<'graph' | 'timeline'>('graph')
  const [inspected, setInspected] = useState<Fact | null>(null)
  const [loading, setLoading] = useState(true)
  const [graphLoading, setGraphLoading] = useState(false)
  const [answerBusy, setBusy] = useState(false)
  const runLock = useRef(false)
  const mounted = useRef(true)
  const [activeJob, setActiveJob] = useState<Job | null>(null)
  const [jobRemote, setJobRemote] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const importWarningNotice = useRef<string | null>(null)
  const [tick, setTick] = useState(0)
  const [search, setSearch] = useState('')
  const [projectSearch, setProjectSearch] = useState('')
  const [reviewFilter, setReviewFilter] = useState('pending')
  const [audit, setAudit] = useState<Audit[]>([])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [tokenDraft, setTokenDraft] = useState(getToken)

  const refresh = useCallback(async () => {
    const sequence = ++refreshSequence.current
    const [newStats, newProjects, newSources, newFacts, newRuntime, newAudit, quality] = await Promise.all([
      request<Stats>(withSource('/stats', sourceId)), request<Project[]>(withSource('/projects', sourceId)), request<Source[]>('/sources'),
      request<Fact[]>(withSource('/facts', sourceId)), request<Runtime>('/runtime'), request<Audit[]>('/reviews'),
      sourceId ? request<SourceAnalysis>(withSource('/sources/analysis', sourceId)).catch(() => null) : Promise.resolve(null),
    ])
    if (sequence !== refreshSequence.current) return
    setStats(newStats); setProjects(newProjects); setSources(newSources); setFacts(newFacts); setRuntime(newRuntime); setAudit(newAudit); setSourceAnalysis(quality)
    if (sourceId && !newSources.some(source => source.id === sourceId)) setError('当前网址指定的数据源不存在，请在来源选择中切换。')
    else if (sourceId && !quality) setError('当前来源已读取，但分析概况暂未能加载，请重试。')
    setProjectId(current => newProjects.some(project => project.id === current) ? current : newProjects[0]?.id || '')
    setInspected(current => current ? newFacts.find(fact => fact.id === current.id) || null : null)
    setTick(value => value + 1)
  }, [sourceId])
  const latestRefresh = useRef(refresh)
  latestRefresh.current = refresh
  const diagramTask = useDiagramJob(latestRefresh)
  const factTask = useDiagramJob(latestRefresh, 'facts')
  const busy = answerBusy || diagramTask.running || factTask.running
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => { let active = true; setLoading(true); refresh().catch(err => { if (active) setError(messageOf(err)) }).finally(() => { if (active) setLoading(false) }); return () => { active = false; refreshSequence.current += 1 } }, [refresh])
  useEffect(() => { if (!notice || notice === importWarningNotice.current) return; const timer = setTimeout(() => setNotice(''), 6500); return () => clearTimeout(timer) }, [notice])
  useEffect(() => {
    const sequence = ++graphSequence.current
    let active = true
    if (page !== 'projects') return
    if (!projectId) { setGraph(null); setVersions([]); setGraphLoading(false); return }
    setGraphLoading(true)
    Promise.all([request<Workflow>(withSource(`/projects/${encodeURIComponent(projectId)}/workflow${version ? `?version=${version}` : ''}`, sourceId)), request<Version[]>(withSource(`/projects/${encodeURIComponent(projectId)}/versions`, sourceId))]).then(([newGraph, newVersions]) => { if (active && sequence === graphSequence.current) { setGraph(newGraph); setVersions(newVersions); setInspected(current => current ? newGraph.facts.find(f => f.id === current.id) || null : null) } }).catch(err => { if (active && sequence === graphSequence.current) { setError(messageOf(err)); setGraph(null) } }).finally(() => { if (active && sequence === graphSequence.current) setGraphLoading(false) })
    return () => { active = false }
  }, [projectId, version, tick, page, sourceId])
  async function run(demo = false) {
    if (runLock.current || busy || loading) return
    if (!demo && runtime?.provider !== 'local-demo' && !sourceId) { setError('大模型分析需要明确的数据范围。请先在顶部选择一个数据源，本次只发送该来源的消息。'); return }
    runLock.current = true
    setBusy(true); setError(''); setActiveJob(null); setStopping(false); setJobRemote(!demo && runtime?.provider === 'helloagents-llm')
    try {
      const response = demo ? await post<{ import: ImportReport; job: Job }>('/demo') : null
      let result = response ? response.job : await post<Job>('/jobs', sourceId ? { source_id: sourceId } : {})
      if (!response) setActiveJob(result)
      while (result.status === 'queued' || result.status === 'running') {
        await new Promise(resolve => setTimeout(resolve, 1000))
        if (!mounted.current) return
        try {
          result = await request<Job>(`/jobs/${encodeURIComponent(result.id)}`)
          setActiveJob(result); setError('')
        } catch { setError('任务进度暂时无法读取，正在重试。任务可能仍在服务器处理，请勿重复启动。') }
      }
      if (!mounted.current) return
      await latestRefresh.current()
      if (result.status === 'failed') throw new Error(result.error || '分析失败，请检查运行日志。')
      if (result.status === 'cancelled') { setNotice(typeof result.progress?.markdown === 'string' ? '已停止生成，已收到的正文保留。不会自动重试。' : '任务已停止，本次分析未写入正式工作流。'); return }
      if (response && response.import.source_id !== sourceId) changeSource(response.import.source_id)
      setVersion(''); setNotice(demo ? '模拟消息已导入并完成重建。' : result.result?.complete === false ? '回答未完整，已保留已输出正文；手动重新生成可能再次计费。' : typeof result.progress?.markdown === 'string' ? '模型回答已保存，可在「模型回答」中查看。' : '工作流已更新，新增事实等待人工审核。')
      if (demo) setPage('projects')
    } catch (err) { if (mounted.current) setError(messageOf(err)) } finally { runLock.current = false; if (mounted.current) { setBusy(false); setStopping(false) } }
  }
  async function stopJob() {
    if (!activeJob || stopping || activeJob.cancel_requested) return
    setStopping(true)
    try { setActiveJob(await post<Job>(`/jobs/${encodeURIComponent(activeJob.id)}/cancel`)); setNotice('已请求停止，正在等待当前模型请求结束。') }
    catch (failure) { setError(messageOf(failure)); setStopping(false) }
  }
  async function handleImported(importedSource?: string, report?: ImportReport) {
    if (importedSource) {
      const summary = report
        ? `实际新增 ${report.imported} 条，跳过 ${report.duplicates} 条已有消息。`
        : '消息已导入。'
      const warnings = report?.warnings.join('；') || ''
      const importNotice = `${summary}${warnings ? ` ${warnings}` : ''} 当前查看对应来源，需要分析时再手动启动。`
      importWarningNotice.current = warnings ? importNotice : null
      setNotice(importNotice)
    }
    if (importedSource && importedSource !== sourceId) changeSource(importedSource)
    else await refresh()
  }
  async function exportData(format: string, project?: string) { try { await download(format, project, sourceId); setNotice('当前范围的导出文件已生成。') } catch (err) { setError(messageOf(err)) } }
  async function deletedSource(result: SourceDeletionResult) {
    graphSequence.current += 1
    setGraph(null); setVersions([]); setInspected(null); setVersion(''); setSourceAnalysis(null)
    setNotice(`已删除来源 ${result.source_id} 的 ${result.messages_deleted} 条本地消息及 ${result.facts_deleted} 条关联事实。`)
    if (sourceId === result.source_id) changeSource('')
    else { try { await refresh() } catch (failure) { setError(`删除已完成，刷新工作空间失败：${messageOf(failure)}。请刷新页面。`) } }
  }
  function changeSource(next: string) {
    refreshSequence.current += 1; graphSequence.current += 1
    setSourceId(next); setVersion(''); setProjectId(''); setGraph(null); setVersions([]); setInspected(null); setSourceAnalysis(null); setSearch(''); setProjectSearch(''); setError(''); setOnlyUnassigned(false)
    const url = new URL(window.location.href); if (next) url.searchParams.set('source', next); else url.searchParams.delete('source'); window.history.replaceState({}, '', url)
  }
  function reviewUnassigned() { navigate('review'); setOnlyUnassigned(true); setReviewFilter('') }
  function chooseProject(id: string) { setProjectId(id); setVersion(''); setInspected(null); setSearch('') }
  function navigate(next: Page) { setPage(next); setInspected(null); setSearch(''); setError('') }
  function reviewed(fact: Fact) { setInspected(fact); setNotice(`事实${reviewNames[fact.review_status]}，审核已记录。`); refresh().catch(err => setError(messageOf(err))) }
  const filteredFacts = useMemo(() => facts.filter(fact => (!reviewFilter || fact.review_status === reviewFilter) && (!onlyUnassigned || !fact.project_id) && (!search || `${fact.summary} ${fact.project_hint || ''} ${fact.actor || ''}`.toLowerCase().includes(search.toLowerCase()))), [facts, reviewFilter, search, onlyUnassigned])
  const project = graph?.project.id === projectId ? graph.project : projects.find(item => item.id === projectId)
  const workflowFacts = graph?.facts.filter(fact => !search || `${fact.summary} ${fact.actor || ''}`.toLowerCase().includes(search.toLowerCase())) || []
  const currentNav = nav.find(item => item.id === page)!
  const liveAnswer = activeJob && jobRemote && activeJob.source_id === sourceId && typeof activeJob.progress?.markdown === 'string' && (answerBusy || activeJob.status !== 'completed' || activeJob.result?.complete === false) ? activeJob : null

  return <div className="app-shell"><aside className="sidebar" aria-label="应用导航与连接设置"><a className="brand" aria-label="溯流项目工作台" href="#" onClick={event => { event.preventDefault(); navigate('projects') }}><span className="brand-mark"><WorkflowIcon size={25} /></span><span>溯流<small>Workflow Atlas</small></span></a><div className="workspace-name"><span className="workspace-avatar">W</span><span>工作流重建工作台<small>本地工作空间</small></span><ChevronDown size={14} /></div><nav aria-label="主导航">{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} aria-label={item.label} title={item.label} onClick={() => navigate(item.id)}><item.icon size={19} /><span>{item.label}</span>{item.id === 'review' && !!stats?.pending_review && <b>{stats.pending_review}</b>}</button>)}</nav><div className="sidebar-bottom"><div className="privacy-indicator"><span /><div>{runtime?.provider === 'local-demo' ? '本地分析模式' : runtime?.provider ? '大模型分析模式' : '等待连接'}<small>{runtime?.provider === 'local-demo' ? '消息不传送至外部模型' : '仅发送明确选定的来源消息'}</small></div></div><button className="nav-item" aria-label="连接设置" title="连接设置" onClick={() => { setTokenDraft(getToken()); setSettingsOpen(true) }}><Settings2 size={18} /><span>连接设置</span></button><div className="sidebar-version">Workflow Atlas <span>v0.1</span></div></div></aside><main className="main"><header className="topbar"><div className="breadcrumb">工作空间<ChevronRight size={14} /><strong>{currentNav.label}</strong></div><div className="top-actions"><span className="local-tag"><ShieldCheck size={14} /> 证据可追溯</span><button className="button" onClick={() => run(true)} disabled={busy || loading}>{busy ? <LoaderCircle size={15} className="spin" /> : <Play size={15} />} 导入模拟数据</button><button className="avatar" aria-label="本地工作空间">W</button></div></header><div className="source-scope-bar"><label>分析来源<select aria-label="分析来源" value={sourceId} disabled={busy} onChange={event => changeSource(event.target.value)}><option value="">全部来源（{sources.length}）</option>{sourceId && !sources.some(source => source.id === sourceId) && <option value={sourceId}>{sourceId}（未找到）</option>}{sources.map(source => <option key={source.id} value={source.id}>{source.id} · {source.message_count} 条消息</option>)}</select></label><span>{runtime?.provider !== 'local-demo' ? sourceId ? `模型分析只发送 ${sourceId} 的消息。` : '模型分析前必须选择一个来源，不支持全部来源发送。' : sourceId ? '统计、图谱、审核与导出均限定在当前来源。' : '选择一个来源，可分别查看导入数据与演示数据。'}</span></div>{error && <div className="alert error-alert" role="alert"><span>{error}</span><button className="icon-button" aria-label="关闭错误" onClick={() => setError('')}><X size={16} /></button></div>}{notice && <div className="alert success-alert" role="status"><CheckCheck size={18} /><span>{notice}</span><button className="icon-button" aria-label="关闭提示" onClick={() => setNotice('')}><X size={16} /></button></div>}{activeJob && <section className="job-progress-panel" aria-label="分析任务进度"><div className="job-progress-heading"><div>{answerBusy ? <LoaderCircle size={17} className="spin" /> : <CheckCheck size={17} />}<strong>{activeJob.status === 'completed' ? activeJob.result?.complete === false ? '回答未完整' : typeof activeJob.progress?.markdown === 'string' ? '回答已结束' : '分析已完成' : activeJob.status === 'failed' ? '分析未完成' : activeJob.status === 'cancelled' ? '任务已停止' : activeJob.cancel_requested ? '正在停止任务' : '正在分析消息'}</strong></div>{answerBusy && <button className="button danger-outline job-progress-stop" disabled={stopping || activeJob.cancel_requested} onClick={stopJob}>{stopping || activeJob.cancel_requested ? '等待停止…' : '停止分析'}</button>}</div><p className="job-progress-source">处理来源：{jobRemote ? activeJob.source_id || '等待来源信息' : '本地全部来源'}{jobRemote && activeJob.source_id ? ' · 仅此来源消息发送到模型服务' : ''}</p><progress className="job-progress-bar" aria-label="消息分析进度" max={activeJob.progress?.total_messages || 1} value={activeJob.progress?.processed_messages || 0} /><div className="job-progress-meta"><span>{typeof activeJob.progress?.markdown === 'string' ? <>输入 {activeJob.progress.total_messages || 0} 条消息 · 已输出 {Array.from(activeJob.progress.markdown).length} 个字符</> : <>已处理 {activeJob.progress?.processed_messages || 0} / {activeJob.progress?.total_messages || 0} 条消息{typeof activeJob.progress?.cached_messages === 'number' && <>，其中 {activeJob.progress.cached_messages} 条复用缓存</>}</>}</span><span>批次 {activeJob.progress?.batch_index || 0} / {activeJob.progress?.total_batches || 0} · {stages[activeJob.progress?.stage || ''] || activeJob.progress?.stage || '等待开始'}</span></div>{activeJob.error && <p className="job-progress-error">{activeJob.error}</p>}{['failed', 'cancelled'].includes(activeJob.status) && <p className="job-progress-source">{typeof activeJob.progress?.markdown === 'string' ? '已收到的正文保留在下方。不会自动重试；手动重新生成可能再次计费。' : <>本次分析未写入正式工作流。{jobRemote && (activeJob.progress?.cached_messages || 0) > 0 ? '本次复用的缓存计数见上方。可使用相同模型配置重新分析此来源。' : '可重新启动分析。'}</>}</p>}{!!activeJob.result?.warnings?.length && <p className="job-progress-source">{activeJob.result.warnings.join('；')}</p>}</section>}{liveAnswer && <section className="live-answer-preview" aria-label="本次模型回答预览"><div className="live-answer-heading"><h2>本次模型回答</h2><span>来源：{liveAnswer.source_id}</span></div><MarkdownAnswer answer={{ markdown: liveAnswer.progress!.markdown!, usage: liveAnswer.progress?.usage, model: liveAnswer.progress?.model, thinking: liveAnswer.progress?.thinking, thinking_controlled: liveAnswer.progress?.thinking_controlled, finish_reason: liveAnswer.progress?.finish_reason, elapsed_ms: liveAnswer.progress?.elapsed_ms, complete: liveAnswer.status === 'completed' && liveAnswer.result?.complete !== false }} running={['queued', 'running'].includes(liveAnswer.status)} cached={(liveAnswer.progress?.cached_messages || 0) > 0} /></section>}{diagramTask.running && <section className="job-progress-panel" aria-label="图谱生成任务"><div className="job-progress-heading"><div><LoaderCircle size={17} className="spin" /><strong>正在根据现有回答生成图谱</strong></div><button className="button danger-outline" disabled={diagramTask.stopping || diagramTask.job?.cancel_requested} onClick={diagramTask.cancel}>{diagramTask.stopping || diagramTask.job?.cancel_requested ? '等待停止…' : '停止图谱生成'}</button></div><p className="job-progress-source">来源：{diagramTask.sourceId} · 额外模型调用，仅使用已保存回答</p><button className="text-button" onClick={() => navigate('projects')}>查看图谱生成进度</button></section>}{factTask.running && <section className="job-progress-panel" aria-label="事实图谱生成任务"><div className="job-progress-heading"><strong>正在生成可交互事实图谱</strong><button className="button danger-outline" disabled={factTask.stopping || factTask.job?.cancel_requested} onClick={factTask.cancel}>{factTask.stopping || factTask.job?.cancel_requested ? '等待停止…' : '停止生成'}</button></div><p className="job-progress-source">来源：{factTask.sourceId} · 使用已保存回答和原始消息核对证据</p><button className="text-button" onClick={() => navigate('projects')}>查看图谱生成进度</button></section>}{loading ? <div className="app-loading"><LoaderCircle size={24} className="spin" /><p>正在读取工作空间…</p></div> : <>
    {page === 'projects' && <ModelReportWorkspace key={sourceId} sourceId={sourceId} refreshToken={tick} remote={runtime?.provider === 'helloagents-llm'} busy={busy} onAnalyze={() => run()} onConfigure={() => navigate('model')} diagramTask={diagramTask} onDiagram={() => { if (!busy) void diagramTask.start(sourceId) }} factTask={factTask} onFacts={() => { if (!busy) void factTask.start(sourceId) }} legacyFactCount={stats?.facts || 0}><section className="workspace-intro"><div><div className="title-with-count"><h1>还原项目的真实进程</h1><span className="mode-pill"><span />{runtime?.provider === 'local-demo' ? '本地规则演示' : runtime?.provider || '未连接'}</span></div><p>从分散的消息中串联任务、决策与交付，每一步都能回到证据。</p></div>{runtime?.provider === 'local-demo' && <button className="button primary" disabled={busy || loading || !stats?.messages} onClick={() => run()}><RefreshCw size={16} className={busy ? 'spin' : ''} /> 更新工作流</button>}</section><div className="metrics-ledger">{[{ label: '原始消息', value: stats?.messages || 0, icon: FileText }, { label: '工作事实', value: stats?.facts || 0, icon: Layers3 }, { label: '项目候选', value: stats?.projects || 0, icon: GitBranch }, { label: '待人工审核', value: stats?.pending_review || 0, icon: ListChecks }].map(item => <div className="metric" key={item.label}><item.icon size={20} /><span>{item.label}</span><strong>{item.value}<small>{item.label === '项目候选' ? '个' : '条'}</small></strong></div>)}</div>{sourceAnalysis && <SourceQuality analysis={sourceAnalysis} onReviewUnassigned={reviewUnassigned} />}{projects.length ? <div className="project-workspace"><aside className="project-rail" aria-label="项目列表"><div className="rail-heading"><h2>全部项目</h2><span>{projects.length}</span></div><label className="project-search"><Search size={14} /><input aria-label="搜索项目" placeholder="搜索项目" value={projectSearch} onChange={event => setProjectSearch(event.target.value)} /></label>{projects.filter(item => item.name.toLocaleLowerCase().includes(projectSearch.toLocaleLowerCase())).map(item => { const count = facts.filter(f => f.project_id === item.id).length; return <button key={item.id} className={`project-item ${item.id === projectId ? 'active' : ''}`} onClick={() => chooseProject(item.id)}><span className="project-glyph"><GitBranch size={18} /></span><strong>{item.name}</strong><span>{count} 条工作事实</span><ChevronRight size={15} /></button> })}{projectSearch && !projects.some(item => item.name.toLocaleLowerCase().includes(projectSearch.toLocaleLowerCase())) && <p className="project-search-empty">没有匹配的项目</p>}{facts.some(f => !f.project_id) && <button className="unassigned" onClick={reviewUnassigned}><CircleHelp size={15} />{facts.filter(f => !f.project_id).length} 条事实待归属</button>}<div className="rail-footer"><span className="legend-dot" />持续追踪已导入消息</div></aside><section className="workflow-panel"><div className="workflow-heading"><div><div className="project-heading"><h2>{project?.name || '选择项目'}</h2><span className="project-status">{project?.analysis_mode === 'model' ? project.status : project?.status === 'completed' ? '已完成' : '追踪中'}</span></div><p>{graph ? `${graph.nodes.length} 个节点${graph.related_nodes?.length ? ` · ${graph.related_nodes.length} 个关联节点` : ''} · ${[...graph.edges, ...(graph.related_edges || [])].filter(edge => edge.relation !== 'precedes').length} 条显式关系 · 最新事实 ${graph.facts.length ? date(graph.facts[graph.facts.length - 1].occurred_at) : '—'}` : '读取项目…'}</p></div><label className="version-control"><Clock3 size={14} /><select aria-label="工作流版本" value={version} onChange={event => { setVersion(event.target.value); setInspected(null) }}><option value="">最新版本{graph && !version ? ` v${graph.version}` : ''}</option>{versions.map(item => <option key={item.version} value={item.version}>v{item.version} · {date(item.created_at)}</option>)}</select></label></div><div className="workspace-toolbar"><div className="segmented"><button className={view === 'graph' ? 'active' : ''} onClick={() => setView('graph')}><Network size={15} />关系图谱</button><button className={view === 'timeline' ? 'active' : ''} onClick={() => setView('timeline')}><Clock3 size={15} />事件时间线</button></div><div className="toolbar-right">{view === 'timeline' && <label className="search-field"><Search size={14} /><input aria-label="搜索项目事实" placeholder="搜索事实" value={search} onChange={e => setSearch(e.target.value)} /></label>}<button className="icon-button" aria-label="导出当前项目 JSON" title="导出当前项目 JSON" onClick={() => exportData('json', projectId)}><ArrowDownToLine size={17} /></button></div></div>{graphLoading ? <div className="graph-loading"><LoaderCircle size={22} className="spin" /> 加载工作流…</div> : graph ? view === 'graph' ? <Graph graph={graph} selectedId={inspected?.id} onSelect={setInspected} /> : <Timeline facts={workflowFacts} selectedId={inspected?.id} onSelect={setInspected} /> : <Empty title="未能加载工作流">请检查服务器连接后重试。</Empty>}{!!graph?.warnings.length && <details className="workflow-warnings"><summary><CircleHelp size={14} /> {graph.warnings.length} 条重建提示</summary><ul>{graph.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></details>}</section><EvidencePanel fact={inspected} historical={!!version} onReviewed={reviewed} onClose={() => setInspected(null)} /></div> : <div className="surface empty-workspace"><Empty title={facts.length ? "已提取事实，项目归属仍需确认" : stats?.messages ? "当前来源尚未形成项目图谱" : "把消息连接成项目的来龙去脉"} action={<div className="scope-empty-actions">{facts.some(fact => !fact.project_id) && <button className="button primary" onClick={reviewUnassigned}><ListChecks size={16} />查看未归属事实</button>}{!!stats?.messages && <button className="button" onClick={() => run()} disabled={busy}><RefreshCw size={16} />更新工作流</button>}{!stats?.messages && <button className="button primary" onClick={() => run(true)} disabled={busy || loading}><Play size={16} />导入模拟数据并重建</button>}<button className="button" onClick={() => navigate('sources')}><Upload size={16} />管理数据源</button></div>}>{stats?.messages ? "原始消息已保留。没有明确项目依据的事实会保持未归属，可在审核页面查看；附件内容尚未读取。" : "从一组模拟飞书消息开始，体验事实提取、图谱重建、证据核验和人工审核。"}</Empty><div className="empty-process"><span>历史消息</span><ArrowRight size={16} /><span>工作事实</span><ArrowRight size={16} /><span>项目图谱</span><ArrowRight size={16} /><span>证据审核</span></div></div>}</ModelReportWorkspace>}
    {page === 'sources' && <SourcePage sources={sources} busy={busy} onProcess={() => run()} onDeleted={deletedSource} onImported={handleImported} />}
    {page === 'runtime' && <RuntimePage runtime={runtime} />}
    {page === 'model' && <ModelSettingsPage busy={busy} sourceId={sourceId} onSaved={refresh} />}
    {page === 'exports' && <ExportPage key={sourceId} projects={projects} facts={facts} onExport={exportData} />}
    {page === 'review' && <div className="page-content"><div className="section-intro"><div><h1>事实审核</h1><p>核对提取结果与原始证据，采纳后才可作为可信训练标签导出。</p></div><span className="review-total"><b>{facts.filter(f => f.review_status === 'accepted').length}</b> / {facts.length} 已采纳</span></div><div className="review-layout"><section className="surface review-list"><div className="review-toolbar"><div className="segmented">{[{ id: 'pending', label: '待审核' }, { id: 'accepted', label: '已采纳' }, { id: 'rejected', label: '已驳回' }, { id: '', label: '全部' }].map(item => <button key={item.id} className={reviewFilter === item.id ? 'active' : ''} onClick={() => setReviewFilter(item.id)}>{item.label}</button>)}</div><label className="search-field"><Search size={15} /><input aria-label="搜索审核事实" placeholder="搜索事实或项目" value={search} onChange={e => setSearch(e.target.value)} /></label></div><div className="review-scope-filters"><label><input type="checkbox" checked={onlyUnassigned} onChange={event => setOnlyUnassigned(event.target.checked)} />仅未归属事实</label><span className="muted">{sourceId ? "当前来源" : "全部来源"}共 {facts.filter(fact => !fact.project_id).length} 条事实待归属</span></div><div className="fact-table-heading"><span>工作事实</span><span>项目 / 时间</span><span>审核状态</span></div>{filteredFacts.map(fact => <button key={fact.id} className={`fact-row ${inspected?.id === fact.id ? 'selected' : ''}`} onClick={() => setInspected(fact)}><span><span className={`kind ${fact.kind}`}>{kinds[fact.kind]}</span><strong>{fact.summary}</strong><small>{fact.verified ? <ShieldCheck size={12} /> : <CircleHelp size={12} />}{fact.verified ? '引文已核验' : '证据待核验'} · {fact.evidence.length} 条证据</small></span><span><strong>{projects.find(p => p.id === fact.project_id)?.name || '待归属'}</strong><small>{date(fact.occurred_at)}</small></span><Badge fact={fact} /></button>)}{!filteredFacts.length && <Empty title="当前没有匹配的事实">切换审核状态或调整搜索词；尚未导入时可使用模拟数据。</Empty>}<div className="table-footer"><Filter size={14} />显示 {filteredFacts.length} 条事实</div></section><EvidencePanel fact={inspected} historical={false} onReviewed={reviewed} onClose={() => setInspected(null)} /></div>{!!audit.filter(item => facts.some(fact => fact.id === item.fact_id)).length && <section className="surface audit-section"><div className="panel-heading"><h2>最近审核记录</h2><span className="muted">{audit.filter(item => facts.some(fact => fact.id === item.fact_id)).length} 条记录</span></div>{audit.filter(item => facts.some(fact => fact.id === item.fact_id)).slice(0, 8).map((item, index) => <div className="audit-row" key={`${item.fact_id}/${index}`}><CheckCheck size={16} /><span><strong>{item.reviewer}</strong> {reviewNames[item.status]}<small>{facts.find(f => f.id === item.fact_id)?.summary || item.fact_id}{item.note ? ` · ${item.note}` : ''}</small></span><time>{date(item.created_at)}</time></div>)}</section>}</div>}
    </>}</main>{settingsOpen && <div className="modal-backdrop" onClick={() => setSettingsOpen(false)}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" onClick={e => e.stopPropagation()}><div className="panel-heading"><h2 id="settings-title">连接设置</h2><button className="icon-button" aria-label="关闭设置" onClick={() => setSettingsOpen(false)}><X size={18} /></button></div><p>服务器配置了访问令牌时，在此填写。令牌仅保留在当前浏览器会话。</p><label>API 访问令牌<input type="password" value={tokenDraft} onChange={e => setTokenDraft(e.target.value)} autoComplete="off" placeholder="未设置令牌的本地服务可留空" autoFocus /></label><div className="modal-actions"><button className="button" onClick={() => setSettingsOpen(false)}>取消</button><button className="button primary" onClick={() => { setToken(tokenDraft.trim()); setSettingsOpen(false); setError(''); setLoading(true); refresh().catch(err => setError(messageOf(err))).finally(() => setLoading(false)) }}>保存并重新连接</button></div></section></div>}</div>
}
