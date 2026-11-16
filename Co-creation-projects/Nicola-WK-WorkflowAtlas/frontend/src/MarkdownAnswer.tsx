import { Children, isValidElement } from 'react'
import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import MermaidDiagram from './MermaidDiagram'
import remarkGfm from 'remark-gfm'
import type { DirectModelAnswer, ModelWorkflowReport } from './types'

export function isDirectAnswer(value: DirectModelAnswer | ModelWorkflowReport | null | undefined): value is DirectModelAnswer {
  return !!value && 'markdown' in value && typeof value.markdown === 'string'
}

const count = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value.toLocaleString('zh-CN') : '未提供'

export default function MarkdownAnswer({ answer, running = false, cached = false }: { answer: Partial<DirectModelAnswer> & Pick<DirectModelAnswer, 'markdown'>; running?: boolean; cached?: boolean }) {
  return <article className="surface markdown-answer" aria-label={running ? '正在生成的模型回答' : '模型回答正文'}>
    <div className="answer-state"><span>{running ? '正在生成回答' : answer.complete ? '回答已结束' : '回答未完整 · 已保留输出原文'}</span>{answer.model && <span>{answer.model}</span>}</div>
    {!running && !answer.complete && <p className="answer-incomplete" role="status">以下是已收到的正文，可能在句子或表格中途结束。不会自动重试；手动重新生成可能再次计费。</p>}
    <div className="markdown-content"><ReactMarkdown skipHtml remarkPlugins={[remarkGfm]} components={{
      pre: ({ children }) => { const parts = Children.toArray(children); const code = parts[0]; return parts.length === 1 && isValidElement<{ className?: string; children?: ReactNode }>(code) && code.props.className?.split(/\s/).includes('language-mermaid') && typeof code.props.children === 'string' ? <MermaidDiagram source={code.props.children.replace(/\n$/, '')} pending={running} /> : <pre>{children}</pre> },
      img: () => <span className="answer-image-omitted">[图片已省略，避免向外部地址发送请求]</span>,
      a: ({ href, children }) => href && (/^https?:\/\//i.test(href) || href.startsWith('#')) ? <a href={href} target={href.startsWith('#') ? undefined : '_blank'} rel="noopener noreferrer" referrerPolicy="no-referrer">{children}</a> : <span>{children}</span>,
      table: ({ children }) => <div className="answer-table-scroll" role="region" tabIndex={0} aria-label="回答中的表格，可横向滚动"><table>{children}</table></div>,
    }}>{answer.markdown}</ReactMarkdown>{!answer.markdown && <p className="answer-waiting">{running ? '等待模型返回正文…' : '模型未返回正文。'}</p>}</div>
    {cached && <p className="answer-cache-note" role="status">缓存回答，以下为原请求用量，本次未调用模型。</p>}<dl className="answer-usage" aria-label="模型实际用量"><div><dt>输入 tokens</dt><dd>{count(answer.usage?.prompt_tokens)}</dd></div><div><dt>输出 tokens</dt><dd>{count(answer.usage?.completion_tokens)}</dd></div><div><dt>思考 tokens（输出明细）</dt><dd>{count(answer.usage?.reasoning_tokens)}</dd></div><div><dt>合计 tokens</dt><dd>{count(answer.usage?.total_tokens)}</dd></div><div><dt>深度思考</dt><dd>{answer.thinking_controlled === true ? answer.thinking ? '已开启' : '已关闭' : answer.thinking_controlled === false ? '服务商默认（未指定）' : '未提供／未知'}</dd></div><div><dt>用时</dt><dd>{typeof answer.elapsed_ms === 'number' && Number.isFinite(answer.elapsed_ms) ? `${(answer.elapsed_ms / 1000).toFixed(1)} 秒` : '未提供'}</dd></div></dl>
    <div className="answer-finish">结束原因：{answer.finish_reason || (running ? '生成中' : '未提供')}<span>思考 tokens 属于输出组成，不另行相加；合计仅展示服务返回值，未提供时不推算，不估算费用。</span></div>
    <details className="answer-raw"><summary>查看原始回答文本</summary><pre>{answer.markdown}</pre></details>
  </article>
}
