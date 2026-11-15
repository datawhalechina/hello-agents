import type { ReactNode } from 'react'
import { ArrowRight, CheckCircle2, CircleHelp, FileText, LoaderCircle } from 'lucide-react'

export const verdictLabels: Record<string, string> = {
  supported: '证据充分',
  partial: '待补充',
  unverified: '未验证',
  missing: '缺少证据',
  needs_review: '待核对',
}

export function Badge({ status, children }: { status?: string; children?: ReactNode }) {
  return (
    <span className={`badge ${status || ''}`}>
      <span className="badge-dot" />
      {children || verdictLabels[status || ''] || status}
    </span>
  )
}

export function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  type = 'button',
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  type?: 'button' | 'submit'
  className?: string
}) {
  return (
    <button
      type={type}
      className={`button ${variant} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

export function EmptyState({
  title,
  description,
  action,
  onAction,
}: {
  title: string
  description: string
  action?: string
  onAction?: () => void
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <FileText size={25} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action && (
        <Button onClick={onAction}>
          {action}
          <ArrowRight size={16} />
        </Button>
      )}
    </div>
  )
}

export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  children?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  )
}

export function Panel({
  title,
  description,
  children,
  action,
  className = '',
}: {
  title: string
  description?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function Notice({ children, good = false }: { children: ReactNode; good?: boolean }) {
  return (
    <div className={`notice ${good ? 'good' : ''}`}>
      {good ? <CheckCircle2 size={16} /> : <CircleHelp size={16} />}
      <span>{children}</span>
    </div>
  )
}

export function Loading({ text }: { text: string }) {
  return (
    <span className="loading-label">
      <LoaderCircle className="spin" size={16} />
      {text}
    </span>
  )
}
