// 论文库组件：上传、列表、选择、删除
import { useRef } from 'react'
import type { Paper, PreprocessStatus } from '../types'

interface PaperLibraryProps {
  papers: Paper[]
  selectedIds: Set<string>
  onToggleSelect: (paperId: string) => void
  onDelete: (paperId: string) => void
  onUpload: (file: File) => void
  uploading: boolean
  disabled?: boolean
}

/** 预处理状态徽章 */
function StatusBadge({ status, label }: { status: PreprocessStatus; label: string }) {
  const cls = status === 'done' ? 'status-done' : status === 'failed' ? 'status-failed' : 'status-pending'
  const text = status === 'done' ? '✓' : status === 'failed' ? '✕' : '○'
  return (
    <span className={`status-badge ${cls}`} title={`${label}: ${status}`}>
      {label} {text}
    </span>
  )
}

export default function PaperLibrary({
  papers,
  selectedIds,
  onToggleSelect,
  onDelete,
  onUpload,
  uploading,
  disabled = false,
}: PaperLibraryProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onUpload(file)
      // 重置 input 以便重复上传同一文件
      e.target.value = ''
    }
  }

  return (
    <div className="paper-library">
      {/* 上传区域 */}
      <div className="upload-area">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          disabled={uploading || disabled}
        />
        <button
          className="btn btn-upload"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || disabled}
        >
          {uploading ? <><span className="spinner" /> 上传中...</> : '+ 上传 PDF'}
        </button>
      </div>

      {/* 论文列表 */}
      <div className="paper-list">
        {papers.length === 0 ? (
          <p className="empty-hint">暂无论文，请上传 PDF 文件</p>
        ) : (
          papers.map((paper) => {
            const selected = selectedIds.has(paper.paper_id)
            const allDone =
              paper.parse_status === 'done' &&
              paper.extract_status === 'done' &&
              paper.index_status === 'done'
            return (
              <div
                key={paper.paper_id}
                className={`paper-item ${selected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
              >
                <label className="paper-checkbox">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onToggleSelect(paper.paper_id)}
                    disabled={disabled}
                  />
                </label>
                <div className="paper-info">
                  <div className="paper-title" title={paper.title || paper.filename}>
                    {paper.title || paper.filename}
                  </div>
                  <div className="paper-filename">{paper.filename}</div>
                  <div className="paper-status">
                    <StatusBadge status={paper.parse_status} label="解析" />
                    <StatusBadge status={paper.extract_status} label="抽取" />
                    <StatusBadge status={paper.index_status} label="索引" />
                    {allDone && <span className="status-badge status-cached">已预处理</span>}
                  </div>
                </div>
                <button
                  className="btn-icon btn-delete"
                  onClick={() => onDelete(paper.paper_id)}
                  disabled={disabled}
                  title="删除论文"
                  aria-label="删除论文"
                >
                  ✕
                </button>
              </div>
            )
          })
        )}
      </div>

      {selectedIds.size > 0 && (
        <div className="selected-count">已选择 {selectedIds.size} 篇论文</div>
      )}
    </div>
  )
}
