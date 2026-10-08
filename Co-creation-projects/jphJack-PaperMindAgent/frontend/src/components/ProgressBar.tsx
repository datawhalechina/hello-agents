// 整体进度条组件：展示 0-1 浮点进度
interface ProgressBarProps {
  /** 0-1 之间的进度值 */
  progress: number
  /** 是否处于运行状态（控制 shimmer 动画） */
  active?: boolean
  /** 标签文字 */
  label?: string
}

/** 将 0-1 浮点格式化为百分比字符串 */
function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return '0%'
  const clamped = Math.max(0, Math.min(1, value))
  return `${Math.round(clamped * 100)}%`
}

export default function ProgressBar({ progress, active = false, label = '整体进度' }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(progress) ? progress : 0))
  return (
    <div className="progress-section">
      <div className="section-label">
        <span>{label}</span>
        <span className="progress-value">{formatPercent(clamped)}</span>
      </div>
      <div className="progress-bar-track" role="progressbar" aria-valuenow={Math.round(clamped * 100)} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={`progress-bar-fill${active ? '' : ' idle'}`}
          style={{ width: `${clamped * 100}%` }}
        />
      </div>
    </div>
  )
}
