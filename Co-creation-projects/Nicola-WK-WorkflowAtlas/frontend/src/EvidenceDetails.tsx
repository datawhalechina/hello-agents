import type { Evidence, Fact, Message } from './types'

const object = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
const string = (value: unknown) => typeof value === 'string' ? value : ''
const stringList = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && !!item) : []
const methods: Record<string, string> = { explicit: '原文明确项目名称', explicit_tag: '原文明确项目标记', section: '同一消息中的项目分节', catalog: '明确项目名称再次出现', reply: '显式回复的项目上下文', model_context: '模型结合原文上下文判断归属', unassigned: '项目依据不足' }

function attribution(fact: Fact) { return object(fact.attributes.project_attribution) }
function supports(fact: Fact): Evidence[] {
  const value = attribution(fact)
  const rows = value.support || value.evidence
  if (!Array.isArray(rows)) return []
  return rows.map(object).filter(row => typeof row.message_id === 'string' && typeof row.source_id === 'string' && typeof row.quote === 'string').map(row => ({ message_id: String(row.message_id), source_id: String(row.source_id), quote: String(row.quote) }))
}

export function AttributionDetails({ fact }: { fact: Fact }) {
  const details = attribution(fact)
  const modelFact = fact.attributes.analysis_mode === 'model'
  const method = string(details.method) || (modelFact ? 'model_context' : '')
  const reported = object(fact.attributes.reported_by)
  const reporter = string(reported.name) || string(fact.attributes.sender_name) || string(reported.id) || string(fact.attributes.sender_id)
  const assigned = stringList(fact.attributes.assigned_actor_names)
  const ids = stringList(fact.attributes.assigned_actor_ids)
  const legacyAssignees = Array.isArray(fact.attributes.assignees) ? fact.attributes.assignees.map(item => { const row = object(item); return string(row.name) || string(row.id) }).filter(Boolean) : []
  const people = assigned.length ? assigned : ids.length ? ids : legacyAssignees
  const explicit = fact.attributes.actor_role === 'explicit_assignee' || people.length > 0
  return <div className="attribution-details"><dl className="fact-details identity-details"><div><dt>发言人</dt><dd>{reporter || (fact.attributes.actor_role === 'reporter' ? fact.actor : '') || '见原始消息'}</dd></div><div><dt>{modelFact ? '模型判断负责人' : '明确指派给'}</dt><dd>{modelFact ? people.join('、') || fact.actor || '未明确' : explicit ? people.join('、') || fact.actor || '原文提及人员' : '原文未明确，不将发言人视为执行者'}</dd></div></dl><div className="attribution-heading">项目归属依据</div><p>{method ? Object.prototype.hasOwnProperty.call(methods, method) ? methods[method] : method : fact.project_id ? '明确项目标记或名称' : '项目依据不足，保持未归属'}</p>{supports(fact).map((support, index) => <blockquote key={`${support.source_id}/${support.message_id}/${index}`}>{support.quote.length > 500 ? <>{support.quote.slice(0, 220)}…<details className="attribution-support-long"><summary>展开完整归属引文</summary><p>{support.quote}</p></details></> : support.quote}<small>消息 {support.message_id}</small></blockquote>)}<small className="attribution-note">归属是待审核的解释，原始引文保留供核对。</small></div>
}

function Highlight({ text, quote }: { text: string; quote: string }) {
  const index = text.indexOf(quote)
  if (index < 0) return <>{text}</>
  return <>{text.slice(0, index)}<mark>{quote}</mark>{text.slice(index + quote.length)}</>
}

export function EvidenceQuote({ fact, evidence, source, index }: { fact: Fact; evidence: Evidence; source: Message | null | undefined; index: number }) {
  const reported = object(fact.attributes.reported_by)
  const name = index === 0 ? string(reported.name) || string(fact.attributes.sender_name) : ''
  const context = supports(fact).some(support => support.message_id === evidence.message_id && support.source_id === evidence.source_id && support.quote === evidence.quote)
  const text = source?.text || evidence.quote
  return <div className={`source-quote ${context ? 'context-quote' : ''}`}><div className="source-meta"><span>{name || source?.sender || evidence.source_id}</span><time>{source && new Date(source.timestamp).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</time></div>{context && <span className="quote-role">项目归属线索</span>}{text.length > 700 ? <><p className="quote-preview">{evidence.quote.length > 400 ? `${evidence.quote.slice(0, 400)}…` : evidence.quote}</p><details className="full-source"><summary>展开完整原始消息（{text.length} 字符）</summary><p><Highlight text={text} quote={evidence.quote} /></p></details></> : <p><Highlight text={text} quote={evidence.quote} /></p>}<div className="source-ref">{evidence.source_id}<br /><span>消息 {evidence.message_id}</span></div></div>
}
