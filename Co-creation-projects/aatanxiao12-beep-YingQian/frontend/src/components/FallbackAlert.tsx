interface FallbackAlertProps {
  message: string
  isFallback: boolean
}

export function FallbackAlert({ message, isFallback }: FallbackAlertProps) {
  const show = isFallback || message.includes('降级')
  if (!show) return null

  return (
    <div className="fallback-alert" role="alert">
      <strong>降级提示</strong>
      <p>{message || '本次结果为降级推荐，仅供参考。'}</p>
    </div>
  )
}
