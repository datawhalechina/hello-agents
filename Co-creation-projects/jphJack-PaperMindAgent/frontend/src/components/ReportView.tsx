// 报告展示组件：用 react-markdown 渲染 Markdown 报告
import ReactMarkdown from 'react-markdown'

interface ReportViewProps {
  /** Markdown 字符串 */
  markdown: string
  /** 是否正在加载 */
  loading?: boolean
}

export default function ReportView({ markdown, loading = false }: ReportViewProps) {
  if (loading) {
    return (
      <div className="report-empty">
        <div className="loading-overlay">
          <span className="spinner" />
          <span>正在生成研究报告...</span>
        </div>
      </div>
    )
  }

  if (!markdown || !markdown.trim()) {
    return (
      <div className="report-empty">
        <div className="empty-icon" aria-hidden>R</div>
        <div className="empty-title">暂无研究报告</div>
        <div className="empty-desc">
          输入本地 PDF 文件夹路径并点击启动分析，七步漏斗链路完成后将在此展示 Markdown 研究提案。
        </div>
      </div>
    )
  }

  return (
    <div className="markdown-body">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  )
}
