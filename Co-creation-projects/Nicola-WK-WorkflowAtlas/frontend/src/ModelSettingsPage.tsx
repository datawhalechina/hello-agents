import { useEffect, useState } from 'react'
import { CheckCheck, CircleHelp, Cpu, KeyRound, LoaderCircle, PlugZap, Save, ShieldCheck } from 'lucide-react'
import { post, request } from './api'
import type { ModelConnectionResult, ModelSettings } from './types'

const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error)

export default function ModelSettingsPage({ busy, sourceId, onSaved }: { busy: boolean; sourceId: string; onSaved: () => Promise<void> }) {
  const [settings, setSettings] = useState<ModelSettings | null>(null)
  const [provider, setProvider] = useState<ModelSettings['provider']>('local-demo')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [clearKey, setClearKey] = useState(false)
  const [authorized, setAuthorized] = useState(false)
  const [batchSize, setBatchSize] = useState(5)
  const [thinking, setThinking] = useState(false)
  const [tested, setTested] = useState(false)
  const [latency, setLatency] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function fill(value: ModelSettings) {
    setSettings(value); setProvider(value.provider); setModel(value.model); setBaseUrl(value.base_url)
    setAuthorized(value.external_data_authorized); setBatchSize(value.batch_size); setThinking(value.thinking ?? false); setTested(value.test_status === 'passed')
    setApiKey(''); setClearKey(false); setLatency(null)
  }
  useEffect(() => {
    let active = true
    request<ModelSettings>('/model/settings').then(value => { if (active) fill(value) }).catch(failure => { if (active) setError(messageOf(failure)) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  function edited() { setTested(false); setLatency(null); setError(''); setNotice('') }
  const officialDeepSeek = (() => { try { const endpoint = new URL(baseUrl); return endpoint.protocol === 'https:' && endpoint.hostname === 'api.deepseek.com' && (model.trim() === 'deepseek-flash' || model.trim().startsWith('deepseek-v4')) } catch { return false } })()
  const blocked = busy || loading || testing || saving
  const hasKey = !clearKey && (!!apiKey.trim() || !!settings?.api_key_configured)
  const canTest = !blocked && !!model.trim() && !!baseUrl.trim() && hasKey
  const canSave = !blocked && (provider === 'local-demo' || (!!model.trim() && !!baseUrl.trim() && hasKey && tested && authorized))

  async function testConnection() {
    if (!canTest) return
    setTesting(true); setError(''); setNotice(''); setTested(false)
    try {
      const result = await post<ModelConnectionResult>('/model/test', { model: model.trim(), base_url: baseUrl.trim(), api_key: apiKey.trim() || null })
      setTested(result.ok); setLatency(result.latency_ms)
      if (result.ok) setNotice('连接测试通过。测试只发送固定公开问题，尚未开始分析数据。')
      else setError(result.detail || '连接测试未通过，请检查地址、模型与密钥。')
    } catch (failure) { setError(messageOf(failure)) }
    finally { setTesting(false) }
  }
  async function save() {
    if (!canSave) return
    setSaving(true); setError(''); setNotice('')
    try {
      const result = await request<ModelSettings>('/model/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider, model: model.trim(), base_url: baseUrl.trim(), api_key: apiKey.trim() || null, clear_api_key: clearKey, external_data_authorized: provider === 'helloagents-llm' && authorized, batch_size: batchSize, thinking: provider === 'helloagents-llm' && officialDeepSeek && thinking }) })
      fill(result)
      setNotice(result.provider === 'helloagents-llm' ? '大模型设置已保存并立即生效。选择一个数据源后，可启动分析。' : clearKey ? '已切回本地规则分析，并清除已保存的模型密钥。' : '已保存为本地规则分析，当前不向模型服务发送消息。')
      try { await onSaved() } catch { setError('设置已保存，工作空间刷新失败。请刷新页面查看最新状态。') }
    } catch (failure) {
      setError(messageOf(failure))
    } finally { setSaving(false) }
  }

  return <div className="page-content model-settings-page"><div className="section-intro"><div><h1>大模型设置</h1><p>在这里连接模型服务、测试接口并选择分析方式，保存后立即生效。</p></div><span className={`badge ${settings?.provider === 'helloagents-llm' ? 'accepted' : 'pending'}`}>{settings?.provider === 'helloagents-llm' ? '模型分析已启用' : '当前使用本地规则'}</span></div>
    {loading ? <div className="model-loading" role="status"><LoaderCircle className="spin" size={21} />读取模型设置…</div> : <div className="model-settings-layout"><form className="surface model-settings-form" onSubmit={event => { event.preventDefault(); save() }}>
      <div className="panel-heading"><h2><Cpu size={18} />模型连接</h2><span>OpenAI 兼容聊天接口</span></div><div className="model-form-body">
        <label>分析方式<select value={provider} disabled={blocked} onChange={event => { setProvider(event.target.value as ModelSettings['provider']); if (event.target.value === 'local-demo') setAuthorized(false); setError(''); setNotice('') }}><option value="local-demo">本地规则分析</option><option value="helloagents-llm">大模型分析</option></select></label>
        <label>服务地址（Base URL）<input type="url" value={baseUrl} disabled={blocked} onChange={event => { setBaseUrl(event.target.value); edited() }} placeholder="https://your-provider.example/v1" maxLength={1000} autoComplete="off" /></label>
        <p className="field-help">填写服务商提供的接口根地址，不包含 /chat/completions。</p>
        <label>模型名称（Model ID）<input value={model} disabled={blocked} onChange={event => { setModel(event.target.value); edited() }} placeholder="填写服务商提供的模型 ID" maxLength={200} autoComplete="off" /></label>
        <label>模型 API Key <span className="key-status">{settings?.api_key_configured ? '已保存，留空保留原密钥' : '尚未保存密钥'}</span><input type="password" value={apiKey} disabled={blocked || clearKey} onChange={event => { setApiKey(event.target.value); edited() }} placeholder={settings?.api_key_configured ? '更换密钥时再填写' : '填写模型服务商的 API Key'} autoComplete="new-password" spellCheck={false} /></label>
        {!!settings?.api_key_configured && <label className="model-check"><input type="checkbox" checked={clearKey} disabled={blocked} onChange={event => { setClearKey(event.target.checked); if (event.target.checked) { setApiKey(''); setProvider('local-demo'); setAuthorized(false) } edited() }} />保存时清除已有模型密钥</label>}
        <div className="model-test-row"><button type="button" className="button" disabled={!canTest} onClick={testConnection}>{testing ? <LoaderCircle size={16} className="spin" /> : <PlugZap size={16} />}测试连接</button><span className={tested ? 'connection-passed' : 'muted'}>{testing ? '正在发送固定测试问题…' : tested ? `连接测试通过${latency !== null ? `，${Math.round(latency)} ms` : ''}` : '启用模型分析前，请先测试连接。'}</span></div>
        <div className="model-analysis-fields"><h2>分析范围与方式</h2>{provider === 'helloagents-llm' && !officialDeepSeek && <p className="model-scope-hint">当前地址或模型不支持此应用的深度思考开关，服务商实际模式未知。</p>}{officialDeepSeek && <><label className="model-check"><input type="checkbox" checked={thinking} disabled={blocked || provider !== 'helloagents-llm'} onChange={event => setThinking(event.target.checked)} /><span>深度思考（DeepSeek 官方接口）</span></label><p className="model-scope-hint">开启后通常需要更多思考时间与 tokens。关闭时使用普通回答模式；此开关仅针对 DeepSeek 官方端点的 deepseek-flash / deepseek-v4 系列。</p></>}<p className="field-help">将所选来源消息直接交给模型，按自然语言与 Markdown 表格回答，不强制输出固定结构或重复引用全文。生成中持续显示已收到的正文。</p><p className="model-scope-hint">输入与输出受所选服务及模型的上下文和配额限制。回答中断或未完整时保留已输出正文，不自动重试；手动重新生成可能再次计费。</p>
          <label className="model-check model-consent"><input type="checkbox" checked={authorized} disabled={blocked || provider !== 'helloagents-llm'} onChange={event => setAuthorized(event.target.checked)} /><span>允许在分析时，将明确选定的单个数据源消息发送到此模型服务。</span></label><p className="model-scope-hint">{sourceId ? <>当前选中来源：<strong>{sourceId}</strong></> : '当前选择了全部来源。启动模型分析前，需在顶部选择一个来源。'}</p>
        </div>
        {settings?.storage_error && <p className="inline-error" role="alert">{settings.storage_error}</p>}{busy && <p className="model-job-note" role="status">正在处理任务。请先停止任务或等待完成，再修改设置。</p>}{error && <p className="inline-error" role="alert">{error}</p>}{notice && <p className="model-save-notice" role="status"><CheckCheck size={17} />{notice}</p>}
      </div><div className="model-form-actions"><span>密钥只写入后端，不回显到页面。</span><button className="button primary" type="submit" disabled={!canSave}>{saving ? <LoaderCircle className="spin" size={16} /> : <Save size={16} />}{provider === 'helloagents-llm' ? '保存并启用模型' : '保存设置'}</button></div>
    </form><aside className="model-setting-notes" aria-label="模型连接说明"><section className="surface"><h2><ShieldCheck size={18} />数据如何发送</h2><p>连接测试只发送一条固定公开问题。开始分析时，仅发送你明确选中的来源消息，其他来源保留在本地。</p><p>请求通过本机后端转发。模型密钥在服务器本地加密保存，浏览器不会长期保存密钥。</p></section><section className="surface"><h2><KeyRound size={18} />与连接设置区分</h2><p>这里填写模型服务商的 API Key。左下角「连接设置」填写的是工作台访问令牌，两者用途不同。</p></section><section className="model-setting-help"><CircleHelp size={17} /><p>新回答保持模型的自然 Markdown 内容，不自动变成图谱、已核验事实或训练标签。模型判断仍需你结合原始消息核对。</p></section></aside></div>}
  </div>
}
