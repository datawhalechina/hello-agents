import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity,
  ArrowRight,
  BriefcaseBusiness,
  ChevronDown,
  ChevronRight,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  X,
} from 'lucide-react'
import { api, connectionEvent } from './api'
import { Badge, Button, Loading } from './components'
import { Workbench } from './context'
import { ActivityPage, Interview, Materials, Overview, Review, SettingsPage } from './pages'
import type { Mode, Page, Settings, Workspace, WorkspaceSummary, RunEvent } from './types'

const navigation: { id: Page; name: string; icon: typeof Activity }[] = [
  { id: 'overview', name: '准备概览', icon: LayoutDashboard },
  { id: 'materials', name: '材料与岗位', icon: FileText },
  { id: 'interview', name: '模拟面试', icon: MessageSquareText },
  { id: 'review', name: '复盘与复练', icon: Target },
  { id: 'activity', name: '运行记录', icon: Activity },
  { id: 'settings', name: '模型与设置', icon: Settings2 },
]

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([])
  const [settings, setSettings] = useState<Settings | null>(null)
  const [connected, setConnected] = useState<boolean | null>(null)
  const [recentTokens, setRecentTokens] = useState<number | null>(null)
  const [mode, setMode] = useState<Mode>('live')
  const [page, setPage] = useState<Page>('overview')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [newWorkspace, setNewWorkspace] = useState(false)
  const [name, setName] = useState('')
  const [role, setRole] = useState('Agent 应用开发工程师')
  const dialog = useRef<HTMLDialogElement>(null)
  const inFlight = useRef(false)
  const unsaved = useRef(false)
  useEffect(() => {
    let active = true
    let checking = false
    const onConnection = (event: Event) => {
      if (active) setConnected((event as CustomEvent<boolean>).detail)
    }
    const check = async () => {
      if (checking) return
      checking = true
      try {
        const health = await api<{ status: string }>(
          '/health',
          'GET',
          undefined,
          AbortSignal.timeout(5000),
        )
        if (active) setConnected(health.status === 'ok')
      } catch {
        if (active) setConnected(false)
      } finally {
        checking = false
      }
    }
    window.addEventListener(connectionEvent, onConnection)
    window.addEventListener('focus', check)
    void check()
    const timer = window.setInterval(check, 15000)
    return () => {
      active = false
      window.clearInterval(timer)
      window.removeEventListener(connectionEvent, onConnection)
      window.removeEventListener('focus', check)
    }
  }, [])
  const setUnsaved = useCallback((value: boolean) => {
    unsaved.current = value
  }, [])
  function mayLeave() {
    return !unsaved.current || window.confirm('当前内容有未保存的修改，确定放弃这些修改？')
  }
  function navigate(next: Page) {
    if (next === page || mayLeave()) setPage(next)
  }
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => {
      if (unsaved.current) {
        event.preventDefault()
        event.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [])

  useEffect(() => {
    let ignore = false
    setRecentTokens(null)
    if (workspace)
      api<RunEvent[]>(`/workspaces/${workspace.id}/events?model_only=true`)
        .then((events) => {
          if (!ignore)
            setRecentTokens(
              events.some((e) => e.tokens != null)
                ? events.reduce((n, e) => n + (e.tokens || 0), 0)
                : null,
            )
        })
        .catch(() => {
          /* 用量读取失败不影响面试流程。 */
        })
    return () => {
      ignore = true
    }
  }, [workspace?.id, workspace?.revision])

  async function refreshSettings() {
    setSettings(await api<Settings>('/settings'))
  }
  async function refreshList() {
    setWorkspaces(await api<WorkspaceSummary[]>('/workspaces'))
  }
  function updateWorkspace(item: Workspace) {
    setWorkspace(item)
    localStorage.setItem('offernote-workspace', item.id)
    refreshList().catch(() => {
      /* The next load retries workspace discovery. */
    })
  }
  async function run(task: () => Promise<void>, label: string) {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(label)
    setError('')
    try {
      await task()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作未完成，请重试。')
    } finally {
      inFlight.current = false
      setBusy('')
    }
  }
  useEffect(() => {
    let ignore = false
    Promise.all([api<WorkspaceSummary[]>('/workspaces'), api<Settings>('/settings')])
      .then(async ([list, config]) => {
        if (ignore) return
        setWorkspaces(list)
        setSettings(config)
        const saved = localStorage.getItem('offernote-workspace')
        const id = list.find((item) => item.id === saved)?.id || list[0]?.id
        if (id) {
          const item = await api<Workspace>(`/workspaces/${id}`)
          if (!ignore) {
            setWorkspace(item)
            localStorage.setItem('offernote-workspace', id)
          }
        }
      })
      .catch((e) => {
        if (!ignore) setError(`无法连接本地服务：${e.message}。请确认后端已启动。`)
      })
    return () => {
      ignore = true
    }
  }, [])
  useEffect(() => {
    if (newWorkspace) dialog.current?.showModal()
    else dialog.current?.close()
  }, [newWorkspace])

  const effectiveMode = workspace?.demo_role ? 'live' : mode

  function startInterview(
    focus: 'all' | 'weak' = 'all',
    count = workspace?.demo_role === 'development' ? 4 : 12,
    sourceSessionId?: string,
    maxTopicTurns = 6,
    demonstration = false,
  ) {
    if (!workspace) return
    const guided = workspace.demo_role === 'development' || demonstration
    run(
      async () => {
        if (guided && (!workspace.analysis || workspace.analysis.mode !== 'live')) {
          updateWorkspace(
            await api<Workspace>(`/workspaces/${workspace.id}/analyze`, 'POST', { mode: 'live' }),
          )
        }
        const item = await api<Workspace>(`/workspaces/${workspace.id}/sessions`, 'POST', {
          mode: effectiveMode,
          demonstration: guided,
          focus,
          count,
          source_session_id: sourceSessionId,
          max_topic_turns: maxTopicTurns,
        })
        updateWorkspace(item)
        setSessionId(item.sessions.at(-1)!.id)
        setPage('interview')
      },
      focus === 'weak' ? '正在规划弱项复练问题…' : '正在围绕经历规划面试问题…',
    )
  }
  function loadDemo() {
    run(async () => {
      const item = await api<Workspace>('/workspaces/demo', 'POST')
      updateWorkspace(item)
      setSessionId('')
      setMode('live')
      setPage('overview')
    }, '正在创建演示工作区…')
  }

  const pages = {
    overview: <Overview />,
    materials: <Materials />,
    interview: <Interview />,
    review: <Review />,
    activity: <ActivityPage />,
    settings: <SettingsPage />,
  }
  return (
    <Workbench.Provider
      value={{
        workspace,
        settings,
        mode: effectiveMode,
        setMode,
        busy,
        navigate,
        setUnsaved,
        updateWorkspace,
        run,
        startInterview,
        sessionId,
        setSessionId,
        refreshSettings,
      }}
    >
      <div className="app-shell">
        <aside className="sidebar">
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault()
              navigate('overview')
            }}
          >
            <span className="brand-mark">
              n<span />
            </span>
            <div>
              <strong>
                OfferNote<span className="brand-period">.</span>
              </strong>
              <span className="brand-caption">求职面试工作台</span>
            </div>
          </a>
          <div className="workspace-picker">
            <span className="workspace-avatar">
              <BriefcaseBusiness size={17} />
            </span>
            <select
              aria-label="切换工作区"
              disabled={!!busy}
              value={workspace?.id || ''}
              onChange={(e) => {
                const id = e.target.value
                if (!mayLeave()) {
                  e.target.value = workspace?.id || ''
                  return
                }
                if (id)
                  run(async () => {
                    updateWorkspace(await api<Workspace>(`/workspaces/${id}`))
                    setSessionId('')
                    setPage('overview')
                  }, '正在加载工作区…')
              }}
            >
              <option value="" disabled>
                选择准备工作区
              </option>
              <optgroup label="演示工作区">
                {['development']
                  .map((role) => workspaces.find((w) => w.demo_role === role))
                  .filter((w): w is WorkspaceSummary => !!w)
                  .map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
              </optgroup>
              {!!workspaces.filter((w) => !w.demo_role).length && (
                <optgroup label="我的工作区">
                  {workspaces
                    .filter((w) => !w.demo_role)
                    .map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                </optgroup>
              )}
            </select>
            <ChevronDown size={13} />
          </div>
          <div className="nav-section-label">工作区</div>
          <nav>
            <button
              className="nav-item"
              disabled={!!busy}
              onClick={() => {
                if (mayLeave()) {
                  setName('')
                  setNewWorkspace(true)
                }
              }}
            >
              <Plus size={18} />
              <span>新建准备目标</span>
            </button>
            {navigation
              .slice(4)
              .reverse()
              .map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${page === item.id ? 'active' : ''}`}
                  onClick={() => navigate(item.id)}
                >
                  <item.icon size={18} />
                  <span>{item.name}</span>
                </button>
              ))}
          </nav>
          <div className="nav-section-label second-label">准备工作台</div>
          <nav>
            {navigation.slice(0, 4).map((item) => (
              <button
                key={item.id}
                className={`nav-item ${page === item.id ? 'active' : ''}`}
                onClick={() => navigate(item.id)}
              >
                <item.icon size={18} />
                <span>{item.name}</span>
                {page === item.id && <span className="active-nav-dot" />}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <span className="note-spark">✦</span>
              <strong>准备得具体一点。</strong>
              <p>
                真实的经历，清晰的证据，
                <br />
                练习属于你的表达。
              </p>
            </div>
            <div className="local-profile">
              <span className="profile-avatar">我</span>
              <div>
                <strong>个人工作空间</strong>
                <span>
                  <span className="online-dot" />
                  本地单用户
                </span>
              </div>
              {workspace && (
                <button
                  title="删除当前工作区"
                  aria-label="删除当前工作区"
                  disabled={!!busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        `删除“${workspace.name}”及其材料、面试记录和日志？此操作无法恢复。`,
                      )
                    )
                      run(async () => {
                        await api(`/workspaces/${workspace.id}`, 'DELETE')
                        localStorage.removeItem('offernote-workspace')
                        setWorkspace(null)
                        setSessionId('')
                        setPage('overview')
                        await refreshList()
                      }, '正在删除工作区…')
                  }}
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="breadcrumb">
              <span>我的工作台</span>
              <ChevronRight size={13} />
              <strong>{navigation.find((item) => item.id === page)?.name}</strong>
            </div>
            <div className="topbar-right">
              {recentTokens != null && (
                <button
                  className="token-counter"
                  title="当前工作区最近 100 条模型消耗记录中已返回的 Token 用量；点击查看明细"
                  onClick={() => navigate('activity')}
                >
                  {recentTokens.toLocaleString()} Token
                </button>
              )}
              <span className="local-status" role="status">
                <span className={connected ? 'online-dot' : 'offline-dot'} />
                {connected === null
                  ? '正在连接本地服务'
                  : connected
                    ? '本地服务已连接'
                    : '本地服务已断开'}
              </span>
              <button className="mode-switch" onClick={() => navigate('settings')}>
                <span className={`mode-indicator ${effectiveMode}`} />
                {effectiveMode === 'demo' ? '离线调试' : '真实模型'}
                <ChevronDown size={12} />
              </button>
              <span className="top-avatar">我</span>
            </div>
          </header>
          <main>
            {error && (
              <div className="error-banner" role="alert">
                <span>{error}</span>
                <button aria-label="关闭错误提示" onClick={() => setError('')}>
                  <X size={17} />
                </button>
              </div>
            )}
            {!workspace && page !== 'settings' ? (
              <div className="onboarding">
                <div className="onboarding-label">
                  <Sparkles size={14} />A LITTLE PREPARATION. A BIG NEXT STEP.
                </div>
                <h1>
                  把经历讲清楚，
                  <br />
                  <span>向下一次机会出发。</span>
                </h1>
                <p>
                  整理简历与岗位，核对真实证据。
                  <br />
                  从一次有针对性的追问开始，练好属于你的表达。
                </p>
                <div className="onboarding-actions">
                  <Button
                    disabled={!!busy}
                    onClick={() => {
                      if (mayLeave()) {
                        setName('')
                        setNewWorkspace(true)
                      }
                    }}
                  >
                    <Plus size={17} />
                    创建我的准备目标
                  </Button>
                  <Button variant="secondary" disabled={!!busy} onClick={loadDemo}>
                    体验演示工作区
                    <ArrowRight size={16} />
                  </Button>
                </div>
                <div className="onboarding-steps">
                  {[
                    [FileText, '整理材料', '保留简历与 JD 原文'],
                    [ShieldCheck, '核对证据', '找到经历与岗位的联系'],
                    [MessageSquareText, '逐题练习', '把反馈变成下一步行动'],
                  ].map(([Icon, title, text]) => {
                    const I = Icon as typeof FileText
                    return (
                      <div key={String(title)}>
                        <I size={22} />
                        <strong>{String(title)}</strong>
                        <span>{String(text)}</span>
                      </div>
                    )
                  })}
                </div>
                <div className="onboarding-foot">
                  <ShieldCheck size={14} />
                  材料在本机保存 · 无需登录 · 真实示范需配置模型
                </div>
              </div>
            ) : (
              pages[page]
            )}
            <footer className="page-footer">
              <span>OfferNote · 准备你的下一步</span>
              <span>真实经历 · 明确边界 · 持续练习</span>
            </footer>
          </main>
        </div>
      </div>
      {busy && (
        <div className="operation-toast" role="status">
          <Loading text={busy} />
          <span>请稍候，结果会自动保存</span>
        </div>
      )}
      <dialog ref={dialog} className="create-dialog" onCancel={() => setNewWorkspace(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            run(async () => {
              const item = await api<Workspace>('/workspaces', 'POST', {
                name,
                role,
              })
              updateWorkspace(item)
              setSessionId('')
              setPage('materials')
              setNewWorkspace(false)
            }, '正在创建工作区…')
          }}
        >
          <div className="dialog-heading">
            <div className="stat-icon violet">
              <BriefcaseBusiness size={21} />
            </div>
            <button type="button" aria-label="关闭新建窗口" onClick={() => setNewWorkspace(false)}>
              <X size={19} />
            </button>
          </div>
          <h2>准备一个新的机会。</h2>
          <p>每个目标独立保存材料、面试记录与复盘。</p>
          <label>
            工作区名称
            <input
              autoFocus
              required
              maxLength={80}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：秋招 · Agent 开发"
            />
          </label>
          <label>
            目标岗位
            <input
              required
              maxLength={120}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="例如：Agent 应用开发工程师"
            />
          </label>
          <div className="dialog-actions">
            <Button variant="secondary" onClick={() => setNewWorkspace(false)}>
              取消
            </Button>
            <Button type="submit" disabled={!!busy || !name.trim() || !role.trim()}>
              创建工作区
              <ArrowRight size={15} />
            </Button>
          </div>
        </form>
      </dialog>
    </Workbench.Provider>
  )
}
