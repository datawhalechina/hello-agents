import { useState, useCallback } from 'react'
import { analyzeStock } from '../api/client'

export function useAnalysis() {
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const analyze = useCallback(async (symbol, market) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await analyzeStock(symbol, market)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || '分析失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setLoading(false)
  }, [])

  return { result, loading, error, analyze, reset }
}