import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, CircleAlert, LoaderCircle, PlugZap, Save } from 'lucide-react'
import { api } from './api'
import { Button, Panel } from './components'
import { useWorkbench } from './context'

interface CheckResult {
  message: string
  duration_ms: number
  tokens: number | null
}

export function ModelConfigPanel() {
  const { settings, refreshSettings, busy, setUnsaved } = useWorkbench()
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [key, setKey] = useState('')
  const [maxTokens, setMaxTokens] = useState(12000)
  const [saving, setSaving] = useState(false)
  const [checking, setChecking] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<CheckResult | null>(null)
  const mounted = useRef(true)
  const dirty =
    !!settings &&
    (baseUrl !== settings.base_url ||
      model !== settings.model ||
      maxTokens !== settings.max_tokens ||
      !!key)
  useEffect(() => {
    if (settings) {
      setBaseUrl(settings.base_url || '')
      setModel(settings.model)
      setMaxTokens(settings.max_tokens || 12000)
    }
  }, [settings])
  useEffect(() => {
    setUnsaved(dirty)
    return () => setUnsaved(false)
  }, [dirty, setUnsaved])
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  useEffect(() => {
    if (!checking) return
    const start = Date.now()
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    )
    return () => window.clearInterval(timer)
  }, [checking])
  async function save() {
    setSaving(true)
    setError('')
    setMessage('')
    setResult(null)
    try {
      await api('/settings', 'PUT', {
        base_url: baseUrl,
        model,
        api_key: key || null,
        max_tokens: maxTokens,
      })
      if (!mounted.current) return
      setKey('')
      await refreshSettings()
      if (mounted.current) setMessage('已写入本机 .env，新请求立即生效。')
    } catch (e) {
      if (mounted.current) setError((e as Error).message)
    } finally {
      if (mounted.current) setSaving(false)
    }
  }
  async function check() {
    setChecking(true)
    setElapsed(0)
    setError('')
    setMessage('')
    setResult(null)
    try {
      const value = await api<CheckResult>('/model-check', 'POST')
      if (mounted.current) setResult(value)
    } catch (e) {
      if (mounted.current) setError((e as Error).message)
    } finally {
      if (mounted.current) setChecking(false)
    }
  }
  const locked = saving || checking || !!busy
  return (
    <Panel
      title="模型连接配置"
      description="OpenAI 兼容 Chat Completions · 模型需支持原生 tools / tool_calls。"
    >
      <div className="model-config-form">
        <label>
          API 基础地址
          <input
            aria-label="API 基础地址"
            value={baseUrl}
            disabled={locked}
            onChange={(e) => {
              setBaseUrl(e.target.value)
              setResult(null)
            }}
            placeholder="https://api.openai.com/v1"
          />
        </label>
        <p className="muted small">填写服务商提供的基础地址，不附加 /chat/completions。</p>
        <label>
          模型 ID
          <input
            aria-label="模型 ID"
            value={model}
            disabled={locked}
            onChange={(e) => {
              setModel(e.target.value)
              setResult(null)
            }}
            placeholder="服务商提供的模型名称"
          />
        </label>
        <label>
          API Key
          <input
            aria-label="API Key"
            type="password"
            autoComplete="new-password"
            value={key}
            disabled={locked}
            onChange={(e) => {
              setKey(e.target.value)
              setResult(null)
            }}
            placeholder={settings?.api_key_configured ? '已配置，留空保留原密钥' : '填写服务商密钥'}
          />
        </label>
        <label>
          最大输出 Token
          <input
            aria-label="最大输出 Token"
            type="number"
            min={1024}
            max={64000}
            step={1}
            value={maxTokens}
            disabled={locked}
            onChange={(e) => {
              setMaxTokens(Number(e.target.value))
              setResult(null)
            }}
          />
        </label>
        <p className="muted small">
          推理模型的思考也占用输出预算；出现截断时可提高此值，具体上限以服务商为准。
        </p>
        <div className="model-config-actions">
          <Button
            disabled={
              locked ||
              !dirty ||
              !baseUrl ||
              !model ||
              (!key && !settings?.api_key_configured) ||
              maxTokens < 1024 ||
              maxTokens > 64000
            }
            onClick={save}
          >
            {saving ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />}{' '}
            {saving ? '正在保存…' : '保存到 .env'}
          </Button>
          <Button
            variant="secondary"
            disabled={locked || dirty || !settings?.configured}
            onClick={check}
          >
            {checking ? <LoaderCircle className="spin" size={17} /> : <PlugZap size={17} />}{' '}
            {checking ? `正在测试 · ${elapsed}s` : '测试模型连接'}
          </Button>
        </div>
        {dirty && <p className="muted small">配置有修改，请先保存再测试。</p>}
        <div
          className={`model-check-feedback ${checking ? 'pending' : error ? 'failed' : result || message ? 'passed' : ''}`}
          role={error ? 'alert' : 'status'}
          aria-live="polite"
          aria-busy={checking}
        >
          {checking ? (
            <>
              <LoaderCircle className="spin" size={24} />
              <div>
                <strong>正在验证连接与原生工具调用</strong>
                <p>发送请求 → 调用校验工具 → 检查结果回传 · 已等待 {elapsed} 秒</p>
              </div>
            </>
          ) : error ? (
            <>
              <CircleAlert size={24} />
              <div>
                <strong>操作未完成</strong>
                <p>{error}</p>
              </div>
            </>
          ) : result ? (
            <>
              <CheckCircle2 size={24} />
              <div>
                <strong>连接及原生工具调用通过</strong>
                <p>
                  {result.message} 耗时 {(result.duration_ms / 1000).toFixed(1)} 秒 · Token{' '}
                  {result.tokens?.toLocaleString() ?? '服务商未返回'}
                </p>
              </div>
            </>
          ) : message ? (
            <>
              <CheckCircle2 size={24} />
              <p>{message}</p>
            </>
          ) : (
            <>
              <PlugZap size={22} />
              <p>测试只发送随机校验值，不读取个人材料。测试通过后可切换真实模型。</p>
            </>
          )}
        </div>
        <p className="muted small">
          配置保存在本机项目 .env。密钥不回显、不写入浏览器存储；后续模型请求使用保存的配置。
        </p>
      </div>
    </Panel>
  )
}
