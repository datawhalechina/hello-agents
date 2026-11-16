import type { ModelReportView } from './types'
import type { DiagramJobState } from './useDiagramJob'

export default function FactGraphPanel({ sourceId, busy, hasAnswer, graph, task, onGenerate }: {
  sourceId: string; busy: boolean; hasAnswer: boolean; graph: ModelReportView['fact_graph'];
  task: DiagramJobState; onGenerate: () => void
}) {
  const current = task.sourceId === sourceId
  const job = current ? task.job : null
  const usage = job?.progress?.usage
  return <section className="surface fact-graph-panel" aria-label="可交互事实图谱生成">
    <div className="section-intro"><div><h2>可交互事实图谱</h2><p>生成项目列表、工作节点、时间线和原文证据，支持人工审核。</p></div>
      <button className="button primary" disabled={busy || !sourceId || !hasAnswer} onClick={onGenerate}>
        {graph ? '更新可交互事实图谱（额外1次调用）' : '生成可交互事实图谱（额外1次调用）'}
      </button>
    </div>
    <p>点击后将当前模型回答和此来源的原始消息发送给已接入的模型，可能计费。</p>
    {!hasAnswer && <p>先在「模型回答」中生成并保存此来源的回答。</p>}
    {graph?.stale && <p className="report-stale">当前事实图谱来自此前的回答、消息或模型配置，可按需更新。</p>}
    {graph && <p>已保存版本 v{graph.version}{graph.cached ? ' · 已复用缓存结果' : ''}</p>}
    {current && task.error && <p className="inline-error" role="alert">{task.error}</p>}
    {job && <div className="fact-graph-result" role="status">
      <p>{task.running ? `正在生成，已收到 ${Array.from(job.progress?.markdown || '').length} 个字符` :
        job.status === 'completed' ? `已保存 ${job.result?.projects || 0} 个项目、${job.result?.facts || 0} 条事实` :
        job.status === 'cancelled' ? '生成已停止' : '事实图谱尚未保存'}</p>
      {usage && <p>{job.progress?.cached_messages ? '原请求用量' : '本次模型用量'} · 输入 {usage.prompt_tokens ?? '未提供'} / 输出 {usage.completion_tokens ?? '未提供'} / 合计 {usage.total_tokens ?? '未提供'} tokens</p>}
      {!task.running && job.status !== 'completed' && job.progress?.markdown && <details><summary>查看已收到的模型输出</summary><pre>{job.progress.markdown}</pre></details>}
    </div>}
  </section>
}
