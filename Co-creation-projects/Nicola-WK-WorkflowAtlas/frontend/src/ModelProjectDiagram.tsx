import MarkdownAnswer, { isDirectAnswer } from './MarkdownAnswer'
import MermaidDiagram, { mermaidBlocks } from './MermaidDiagram'
import type { ModelReportView } from './types'
import type { DiagramJobState } from './useDiagramJob'

export default function ModelProjectDiagram({ value, sourceId, busy, remote, task, onGenerate, onAnswer, onLegacy }: { value: ModelReportView | null; sourceId: string; busy: boolean; remote: boolean; task: DiagramJobState; onGenerate: () => void; onAnswer: () => void; onLegacy: () => void }) {
  const answer = isDirectAnswer(value?.report) ? value.report : null
  const embedded = answer ? mermaidBlocks(answer.markdown) : []
  const generated = value?.diagram
  const currentTask = task.sourceId === sourceId
  const job = currentTask ? task.job : null
  const preview = job && (task.running || job.status !== 'completed' || job.result?.complete === false)
  const live = job?.progress
  return <div className="page-content model-diagram-page"><div className="section-intro"><div><h1>项目图谱</h1><p>展示模型回答中的项目和流程图示；历史事实图谱在独立入口保留。</p></div></div><p className="diagram-disclosure">图示由模型绘制，非核验事实。节点、关联及完成状态仍需结合原文判断；图示不产生训练标签。</p>
    {value?.stale && <div className="report-stale" role="status"><strong>旧回答图示 · 来源或模型配置已变化</strong><p>以下内容来自已保存的旧回答，不代表最新来源。可先查看模型回答，再决定是否重新生成。</p></div>}
    {embedded.length ? <><p className="diagram-origin">直接使用当前保存回答中的图示，本次仅在本地绘制，未额外调用模型。</p>{!answer?.complete && <p className="report-stale">回答未完整，图示也可能不完整。</p>}{embedded.map((source, index) => <MermaidDiagram key={index} source={source} />)}</> : <>
      {generated && !value?.diagram_stale ? <><p className="diagram-origin">根据现有回答额外生成的图示</p><MarkdownAnswer answer={generated} cached={value?.diagram_cached === true} /></> : <div className="surface report-guidance"><h2>{!sourceId ? '先选择一个数据源' : answer ? '当前回答还没有项目图示' : '此来源尚无可绘制的直接回答'}</h2><p>{answer ? '纯文字回答未包含 Mermaid 图示。这不代表模型没有发现项目。可以仅根据现有回答补画图谱，不再发送原始消息。' : '先查看或生成模型回答。历史结构化项目与事实仍可在独立入口查看。'}</p><button className="button" onClick={onAnswer}>查看模型回答</button></div>}
      {value?.diagram_stale && generated && <details className="stale-diagram"><summary>查看旧图示（回答、来源或模型配置已变化，不代表当前内容）</summary><MarkdownAnswer answer={generated} cached={value.diagram_cached === true} /></details>}
      {answer && !!answer.markdown.trim() && <div className="diagram-generate-action"><button className="button primary" disabled={busy || !sourceId || !remote} onClick={onGenerate}>{generated && !value?.diagram_stale ? '重新根据现有回答生成图谱（额外1次调用）' : '根据现有回答生成图谱（额外1次调用）'}</button><p>仅在点击后发起额外模型调用，可能计费；只使用当前保存的回答文本。失败或格式错误不自动重试。{value?.stale ? '当前回答已过期，补画图示仍基于这份旧回答。' : ''}{!remote ? '请先在大模型设置启用模型。' : ''}</p></div>}
    </>}
    {currentTask && task.error && <p className="inline-error" role="alert">{task.error}</p>}{preview && <section className="diagram-job-preview" aria-label="本次图谱生成预览"><h2>{task.running ? '正在生成图谱' : job.status === 'cancelled' ? '图谱生成已停止' : '图谱未完整，已保留输出'}</h2><p>来源：{sourceId}。仅为图示补充任务，不修改原回答与历史事实。</p><MarkdownAnswer answer={{ markdown: live?.markdown || '', complete: job.status === 'completed' && job.result?.complete !== false, usage: live?.usage, model: live?.model, thinking: live?.thinking, thinking_controlled: live?.thinking_controlled, elapsed_ms: live?.elapsed_ms, finish_reason: live?.finish_reason }} running={task.running} /></section>}
    <div className="diagram-legacy-link"><button className="button" onClick={onLegacy}>打开历史事实图谱</button><span>历史事实数量不会用来判断当前回答是否包含项目。</span></div>
  </div>
}
