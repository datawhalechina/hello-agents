import { CircleHelp, FileText, ListChecks, ShieldCheck } from 'lucide-react'
import type { SourceAnalysis } from './types'
const methodNames: Record<string, string> = { explicit: '明确项目名称', explicit_tag: '明确项目标记', section: '同消息项目分节', catalog: '明确名称重提', reply: '显式回复上下文', unassigned: '依据不足' }

export default function SourceQuality({ analysis, onReviewUnassigned }: { analysis: SourceAnalysis; onReviewUnassigned: () => void }) {
  return <section className="source-quality" aria-label="当前来源最新分析概况">
    <div className="quality-heading"><FileText size={17} /><h2>当前来源最新分析概况</h2><span>{analysis.messages} 条原始消息</span></div>
    <dl className="quality-counts">
      <div><dt>文本与富文本</dt><dd>{analysis.textual_messages}<small> 条消息</small></dd></div>
      <div><dt>提取出事实的消息</dt><dd>{analysis.extracted_messages}<small> 条</small></dd></div>
      <div><dt>已归属项目的事实</dt><dd>{analysis.assigned_facts}<small> / {analysis.facts} 条</small></dd></div>
      <div><dt>含回复线索</dt><dd>{analysis.reply_messages}<small> 条消息</small></dd></div>
    </dl>
    <div className="quality-findings">
      <p><CircleHelp size={15} /> {analysis.attachment_messages} 条图片、音视频或其他非文本消息保留元数据，内容尚未读取。</p>
      <p><ShieldCheck size={15} /> {analysis.verified_facts} 条事实的原文引用通过核验；归属和解释仍需人工审核。</p>
      {analysis.unassigned_facts > 0 && <button className="text-button" onClick={onReviewUnassigned}><ListChecks size={15} />查看 {analysis.unassigned_facts} 条未归属事实</button>}
    </div>
    <p className="quality-note">这些统计表示提取覆盖与归属情况，不代表分析准确率。没有明确项目依据的信息保持未归属。项目候选按原文字面名称识别，名称变体尚未自动合并。</p>
    <details className="quality-details"><summary>查看消息类型与归属方法</summary><div className="quality-breakdown"><div><h3>消息类型</h3>{Object.entries(analysis.message_types).map(([kind, count]) => <span key={kind}>{kind}<b>{count}</b></span>)}</div><div><h3>归属依据</h3>{Object.entries(analysis.attribution_methods).map(([method, count]) => <span key={method}>{Object.prototype.hasOwnProperty.call(methodNames, method) ? methodNames[method] : method}<b>{count}</b></span>)}</div></div></details>
  </section>
}
