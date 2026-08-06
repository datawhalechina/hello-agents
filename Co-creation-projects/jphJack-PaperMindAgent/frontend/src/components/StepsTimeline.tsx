// 七步漏斗链路进度时间线组件
import { STAGE_LIST } from '../types'
import type { ProgressEvent, StageKey, StepStatus } from '../types'

interface StepsTimelineProps {
  /** 已收到的进度事件，按 stage 聚合保留最新一条 */
  eventsByStage: Record<StageKey, ProgressEvent | undefined>
}

/** 状态文案映射 */
const STATUS_LABEL: Record<StepStatus, string> = {
  pending: '待执行',
  running: '运行中',
  done: '完成',
  failed: '失败',
  degraded: '降级',
  cached: '复用缓存',
}

/** 步骤序号图标：未开始显示数字，已完成显示对勾，失败显示叉，降级显示感叹号，缓存显示勾号 */
function StepIcon({ status, index }: { status: StepStatus; index: number }) {
  if (status === 'done') return <span aria-hidden>✓</span>
  if (status === 'failed') return <span aria-hidden>✕</span>
  if (status === 'degraded') return <span aria-hidden>!</span>
  if (status === 'cached') return <span aria-hidden>↻</span>
  return <span aria-hidden>{index}</span>
}

/** 根据事件状态推导步骤展示状态 */
function deriveStatus(event: ProgressEvent | undefined): StepStatus {
  if (!event) return 'pending'
  if (event.status === 'running') return 'running'
  if (event.status === 'done') return 'done'
  if (event.status === 'failed') return 'failed'
  if (event.status === 'degraded') return 'degraded'
  if (event.status === 'cached') return 'cached'
  return 'pending'
}

export default function StepsTimeline({ eventsByStage }: StepsTimelineProps) {
  return (
    <div className="timeline">
      {STAGE_LIST.map((stage, idx) => {
        const event = eventsByStage[stage.key]
        const status = deriveStatus(event)
        const isActive = status === 'running'
        return (
          <div
            key={stage.key}
            className={`timeline-step${isActive ? ' active' : ''}`}
          >
            <div className="step-marker">
              <div className={`step-icon ${status}`} aria-label={`步骤 ${idx + 1} 状态: ${STATUS_LABEL[status]}`}>
                <StepIcon status={status} index={idx + 1} />
              </div>
              <div className="step-line" />
            </div>
            <div className="step-body">
              <div className="step-header">
                <span className="step-name">{stage.label}</span>
                <span className={`step-status-tag ${status}`}>{STATUS_LABEL[status]}</span>
              </div>
              <p className="step-desc">{stage.description}</p>
              {event?.message ? (
                <div className={`step-message ${status}`}>{event.message}</div>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}
