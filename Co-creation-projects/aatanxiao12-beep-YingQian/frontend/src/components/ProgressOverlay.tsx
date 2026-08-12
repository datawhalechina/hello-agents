import type { ProgressStage } from '../types'
import { PROGRESS_STAGES } from '../types'

interface ProgressOverlayProps {
  active: boolean
  stageIndex: number
}

export function ProgressOverlay({ active, stageIndex }: ProgressOverlayProps) {
  if (!active) return null

  return (
    <div className="progress-overlay" role="status" aria-live="polite">
      <div className="progress-panel">
        <p className="progress-kicker">正在生成片单</p>
        <ol className="progress-stages">
          {PROGRESS_STAGES.map((label: ProgressStage, i) => {
            const state =
              i < stageIndex ? 'done' : i === stageIndex ? 'current' : 'pending'
            return (
              <li key={label} className={`progress-stage progress-stage--${state}`}>
                <span className="progress-dot" aria-hidden="true" />
                <span>{label}</span>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}
