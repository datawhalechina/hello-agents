import { ModelConfigPanel } from './model-config'
import { AgentReview } from './agent-interview'
import { useEffect, useState } from 'react'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Download,
  FileText,
  MessageSquareText,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
} from 'lucide-react'
import { api, dateLabel } from './api'
import { Badge, Button, EmptyState, Notice, PageHeading, Panel, verdictLabels } from './components'
import { useWorkbench } from './context'
import type { RunEvent, Session, Workspace } from './types'

export function DemonstrationIntro() {
  const { workspace: w, settings, busy, navigate, startInterview, setSessionId } = useWorkbench()
  if (w?.demo_role !== 'development') return null
  const active = [...w.sessions].reverse().find((s) => s.demonstration && s.status !== 'completed')
  return (
    <Panel
      title="跟着真实模型，体验一场面试"
      description="虚构 Agent 开发项目 · 面试官、示范候选人和独立评审均调用所配模型。"
    >
      <p>
        进入题目后模型会自动作答，阅读后提交，观察面试官继续追问；完成后查看真实评分、优缺点与逐题参考答案。
      </p>
      <p className="muted small">
        每道新题会调用模型生成回答并产生用量；重开已有题目会读取已保存草稿。示范不代表你的能力，也不保证高分；默认最多
        4 轮。
      </p>
      <Button
        disabled={!!busy}
        onClick={() => {
          if (!settings?.configured) {
            navigate('settings')
            return
          }
          if (active) {
            setSessionId(active.id)
            navigate(active.status === 'active' ? 'interview' : 'review')
          } else startInterview('all', 4, undefined, 3, true)
        }}
      >
        <Sparkles size={16} />
        {!settings?.configured ? '先配置真实模型' : active ? '继续真实示范' : '开始真实示范（4轮）'}
      </Button>
    </Panel>
  )
}

export function Overview() {
  const {
    workspace: w,
    navigate,
    busy,
    startInterview,
    run,
    updateWorkspace,
    mode,
  } = useWorkbench()
  if (!w) return null
  const a = w.analysis
  const finished = w.sessions.filter((s) => s.status === 'completed')
  const turns = w.sessions.flatMap((s) => s.turns)
  const evidence = a?.requirements.filter((r) => r.evidence_verified).length || 0
  const weak = [...new Set(finished.flatMap((s) => s.report?.weak_topics || []))]
  const analyze = () =>
    run(async () => {
      updateWorkspace(await api<Workspace>(`/workspaces/${w.id}/analyze`, 'POST', { mode }))
      navigate('materials')
    }, '正在核对经历与岗位证据…')
  return (
    <>
      <PageHeading
        eyebrow="YOUR NEXT CHAPTER"
        title="每一次准备，都更有底气。"
        description="把真实经历讲清楚，让每一个亮点都有证据。"
      >
        <Button variant="secondary" onClick={() => navigate('materials')}>
          <FileText size={16} />
          管理材料
        </Button>
        <Button disabled={!!busy || !a} onClick={() => startInterview()}>
          <Play size={15} />
          开始模拟面试
        </Button>
      </PageHeading>
      <DemonstrationIntro />
      <section className="welcome-banner">
        <div>
          <span className="banner-label">
            <span className="live-dot" />
            当前准备目标
          </span>
          <h2>{w.role}</h2>
          <p>从经历出发，找到证据，练好下一次表达。</p>
          <button className="text-button" onClick={() => navigate('materials')}>
            查看岗位与简历 <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-card">
            <ShieldCheck size={27} />
            <span>真实经历</span>
            <strong>清晰表达</strong>
            <span className="art-line" />
            <span className="art-line short" />
          </div>
          <span className="art-spark">✦</span>
          <span className="art-dot" />
        </div>
      </section>
      <div className="stats-grid">
        {[
          {
            icon: FileText,
            number: `${Number(!!w.resume) + Number(!!w.job)}`,
            label: '准备材料',
            detail: '简历与目标岗位',
            color: 'blue',
          },
          {
            icon: ShieldCheck,
            number: `${evidence}`,
            label: '相关原文证据',
            detail: a ? `已整理 ${a.requirements.length} 条岗位要求` : '先完成一次证据分析',
            color: 'violet',
          },
          {
            icon: MessageSquareText,
            number: `${finished.length}`,
            label: '已完成面试',
            detail: `累计回答 ${turns.length} 道问题`,
            color: 'green',
          },
          {
            icon: Target,
            number: `${weak.length}`,
            label: '待复练主题',
            detail: '来自已完成面试的反馈',
            color: 'orange',
          },
        ].map((s) => (
          <div className="stat-card" key={s.label}>
            <div className={`stat-icon ${s.color}`}>
              <s.icon size={19} />
            </div>
            <span className="stat-label">{s.label}</span>
            <strong>
              {s.number}
              <small>{s.label.includes('面试') ? '场' : '项'}</small>
            </strong>
            <p>{s.detail}</p>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <Panel
          title="你的准备路径"
          description="从材料到复练，循序渐进。"
          action={
            <span className="muted small">
              {Number(!!w.resume && !!w.job) + Number(!!a) + Number(finished.length > 0)} / 3 已完成
            </span>
          }
        >
          {[
            {
              title: '整理你的真实经历',
              text: '保存简历和目标 JD，检查数字、日期与职责。',
              done: !!w.resume && !!w.job,
              action: () => navigate('materials'),
              cta: '整理材料',
            },
            {
              title: '找出准备重点',
              text: '看岗位缺口、补充证据，再确定优先练习主题。',
              done: !!a,
              action: a ? () => navigate('materials') : analyze,
              cta: a ? '查看准备重点' : '分析材料',
            },
            {
              title: '把经历讲清楚',
              text: '一次一问，基于回答追问，再针对弱项复练。',
              done: finished.length > 0,
              action: () => startInterview(),
              cta: '开始练习',
            },
          ].map((step, i) => (
            <div className="path-step" key={step.title}>
              <span className={`step-index ${step.done ? 'done' : ''}`}>
                {step.done ? <Check size={15} /> : `0${i + 1}`}
              </span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
              <button
                disabled={!!busy || (i > 0 && (!w.resume || !w.job)) || (i === 2 && !a)}
                className="text-button"
                onClick={step.action}
              >
                {step.cta}
                <ChevronRight size={14} />
              </button>
            </div>
          ))}
        </Panel>
        <Panel
          title="下一步，练得更具体"
          description="让项目经历经得起进一步追问。"
          className="coach-panel"
        >
          <div className="coach-icon">
            <Sparkles size={22} />
          </div>
          <h3>从“我用过”，到“我为什么这样做”。</h3>
          <p>
            准备一个具体案例，讲清个人动作、技术取舍和验证结果。真实的细节，比堆叠术语更有说服力。
          </p>
          <div className="mini-tags">
            <span>个人边界</span>
            <span>实现细节</span>
            <span>结果证据</span>
          </div>
          <button className="text-button" onClick={() => navigate('materials')}>
            查看我的准备重点
            <ArrowRight size={15} />
          </button>
        </Panel>
      </div>
      <Panel
        title="最近的练习"
        description="每次回答与反馈都会留在这里。"
        action={
          <button className="text-button" onClick={() => navigate('review')}>
            全部复盘
            <ArrowRight size={14} />
          </button>
        }
      >
        {!w.sessions.length ? (
          <div className="inline-empty">
            <MessageSquareText size={21} />
            <div>
              <strong>还没有面试记录</strong>
              <p>先核对材料，再开启第一场模拟面试。</p>
            </div>
            <span className="muted small">不急，从一次回答开始。</span>
          </div>
        ) : (
          w.sessions
            .slice()
            .reverse()
            .slice(0, 3)
            .map((s) => <SessionRow session={s} key={s.id} />)
        )}
      </Panel>
    </>
  )
}

function SessionRow({ session: s }: { session: Session }) {
  const { setSessionId, navigate } = useWorkbench()
  return (
    <button
      className="session-row"
      onClick={() => {
        setSessionId(s.id)
        navigate(s.status === 'active' ? 'interview' : 'review')
      }}
    >
      <div className="session-icon">
        <MessageSquareText size={18} />
      </div>
      <div>
        <strong>
          {s.demonstration
            ? '真实模型示范面试'
            : s.focus === 'weak'
              ? '弱项专项复练'
              : '项目经历模拟面试'}
        </strong>
        <p>
          {dateLabel(s.created_at)} · {s.mode === 'demo' ? '演示模式' : '真实模型'}
        </p>
      </div>
      <span className="muted small">
        {s.turns.length} / {s.budget?.total_turns || s.questions.length} 轮
      </span>
      <Badge status={s.status === 'completed' ? 'supported' : 'partial'}>
        {s.status === 'completed' ? '已复盘' : s.status === 'awaiting_report' ? '评审中' : '进行中'}
      </Badge>
      <ChevronRight size={16} />
    </button>
  )
}

export function Materials() {
  const { workspace: w, updateWorkspace, run, busy, mode, navigate, setUnsaved } = useWorkbench()
  const [resume, setResume] = useState(w?.resume || '')
  const [job, setJob] = useState(w?.job || '')
  const [fileNotice, setFileNotice] = useState('')
  useEffect(() => {
    setResume(w?.resume || '')
    setJob(w?.job || '')
  }, [w?.id, w?.revision])
  useEffect(() => {
    setUnsaved(!!w && (resume !== w.resume || job !== w.job))
    return () => setUnsaved(false)
  }, [resume, job, w, setUnsaved])
  if (!w) return null
  const dirty = resume !== w.resume || job !== w.job
  async function save(analyze = false) {
    await run(
      async () => {
        const saved = await api<Workspace>(`/workspaces/${w!.id}/materials`, 'PUT', { resume, job })
        updateWorkspace(saved)
        setUnsaved(false)
        if (analyze) {
          updateWorkspace(
            await api<Workspace>(`/workspaces/${w!.id}/analyze`, 'POST', {
              mode,
            }),
          )
          navigate('materials')
        } else setFileNotice('材料已保存。修改后的材料需要重新分析。')
      },
      analyze ? '保存材料并核对原文证据…' : '正在保存材料…',
    )
  }
  return (
    <>
      <PageHeading
        eyebrow="START WITH YOUR STORY"
        title="真实的材料，是准备的起点。"
        description="一份简历，一个目标岗位。先把原文保留下来，再分析差距。"
      >
        <Button variant="secondary" disabled={!!busy || !dirty} onClick={() => save()}>
          保存材料{dirty && <span className="unsaved-dot" />}
        </Button>
        <Button
          disabled={!!busy || resume.trim().length < 30 || job.trim().length < 20}
          onClick={() => save(true)}
        >
          <Sparkles size={16} />
          保存并分析
        </Button>
      </PageHeading>
      <div className="editor-grid">
        <Panel
          title="我的简历"
          description="上传文件或直接粘贴文本，提取后可自行核对。"
          action={
            <label className={`button secondary small-button ${busy ? 'disabled' : ''}`}>
              <Upload size={14} />
              导入文件
              <input
                type="file"
                accept=".pdf,.docx,.md,.txt"
                disabled={!!busy}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  const body = new FormData()
                  body.append('file', file)
                  run(async () => {
                    const result = await api<{ text: string; notice: string }>(
                      '/extract',
                      'POST',
                      body,
                    )
                    setResume(result.text)
                    setFileNotice(`${file.name} 已提取。${result.notice}请保存材料。`)
                  }, '正在提取简历文字…')
                  e.target.value = ''
                }}
              />
            </label>
          }
        >
          <textarea
            aria-label="简历原文"
            className="document-editor"
            value={resume}
            maxLength={24000}
            onChange={(e) => setResume(e.target.value)}
            placeholder={
              '例如：\n项目名称、背景与目标\n你负责哪些部分，使用了什么技术？\n怎样验证结果，有哪些尚未完成的工作？'
            }
          />
          <div className="editor-footer">
            <span>PDF / DOCX / MD / TXT · 最大 5 MB</span>
            <span>{resume.length.toLocaleString()} / 24,000 字符</span>
          </div>
        </Panel>
        <Panel title="目标岗位 JD" description="保留职责、任职要求与加分项的完整原文。">
          <textarea
            aria-label="岗位JD原文"
            className="document-editor"
            value={job}
            maxLength={16000}
            onChange={(e) => setJob(e.target.value)}
            placeholder={
              '粘贴目标岗位描述…\n\n建议包含：\n• 岗位职责\n• 必备技能与经验\n• 加分项与其他要求'
            }
          />
          <div className="editor-footer">
            <span>仅用于当前工作区的准备与分析</span>
            <span>{job.length.toLocaleString()} / 16,000 字符</span>
          </div>
        </Panel>
      </div>
      {fileNotice && <Notice good>{fileNotice}</Notice>}
      <Notice>
        文字版 PDF 识别更稳定。扫描图片暂不支持
        OCR。保存材料后旧分析会失效，历史面试仍保留当时的问题与回答。
      </Notice>
      {dirty && <div className="save-hint">有未保存的修改，离开此页面前请保存。</div>}
      {!dirty && <PreparationSuggestions />}
    </>
  )
}

function PreparationSuggestions() {
  const { workspace: w, busy, run, updateWorkspace, startInterview } = useWorkbench()
  if (!w?.analysis) return null
  const a = w.analysis
  const priorities = a.requirements
    .filter((r) => r.status !== 'supported')
    .sort((left, right) => {
      const rank = { high: 0, medium: 1, low: 2 }
      return rank[left.priority || 'medium'] - rank[right.priority || 'medium']
    })
  return (
    <section className="preparation-results" aria-label="分析结果与准备重点">
      <Panel
        title="分析结果与准备重点"
        description="把分析变成下一步准备；材料未覆盖不等于能力不足。"
        action={
          <Button disabled={!!busy} onClick={() => startInterview()}>
            <Play size={15} />
            开始针对性面试
          </Button>
        }
      >
        <p>{a.summary}</p>
        <p className="muted small">
          {a.mode === 'live' ? '真实模型分析' : '离线调试分析'} · {dateLabel(a.created_at)}
        </p>
        {a.warnings.map((text) => (
          <Notice key={text}>{text}</Notice>
        ))}
        {priorities.some((r) => !r.preparation_action) && (
          <p className="muted small">
            旧分析未包含逐项准备任务；重新点击“保存并分析”可生成具体建议。
          </p>
        )}
        {!priorities.length ? (
          <Notice good>
            材料已覆盖本次提取的岗位要求。下一步通过面试验证实现细节、个人贡献和结果依据。
          </Notice>
        ) : (
          <div className="preparation-priorities">
            {priorities.map((r, i) => (
              <article className="preparation-priority" key={r.id}>
                <div className="row-between">
                  <span className="topic-label">
                    {String(i + 1).padStart(2, '0')} · {r.topic}
                    {r.priority === 'high'
                      ? ' · 优先准备'
                      : r.priority === 'low'
                        ? ' · 后续补充'
                        : ''}
                  </span>
                  <Badge status={r.status} />
                </div>
                <h3>{r.title}</h3>
                <p>{r.reason}</p>
                {r.preparation_action && (
                  <p className="preparation-action">
                    <strong>下一步：</strong>
                    {r.preparation_action}
                  </p>
                )}
                <details>
                  <summary>查看判断依据</summary>
                  <p className="muted small">
                    岗位原文{!r.requirement_verified && '（未通过原文校验）'}
                  </p>
                  <blockquote>{r.requirement_quote}</blockquote>
                  {r.evidence_quote && (
                    <>
                      <p className="muted small">简历原文{!r.evidence_verified && '（需核对）'}</p>
                      <blockquote>{r.evidence_quote}</blockquote>
                    </>
                  )}
                </details>
              </article>
            ))}
          </div>
        )}
        <details className="preparation-details">
          <summary>
            查看已覆盖的岗位要求（
            {a.requirements.filter((r) => r.status === 'supported').length}）
          </summary>
          {a.requirements
            .filter((r) => r.status === 'supported')
            .map((r) => (
              <article className="preparation-priority" key={r.id}>
                <h3>{r.title}</h3>
                <p>{r.reason}</p>
                <blockquote>{r.evidence_quote}</blockquote>
              </article>
            ))}
        </details>
        <details className="preparation-details">
          <summary>面试将核验的经历主张（{a.claims.length}）</summary>
          {a.claims.map((claim) => (
            <article className="preparation-priority" key={claim.id}>
              <span className="topic-label">{claim.topic}</span>
              <h3>{claim.text}</h3>
              <blockquote>{claim.quote}</blockquote>
              <p className="muted small">
                准备说明自己完成了什么、为何这样做，以及如何验证。原文存在不代表实际能力已核实。
              </p>
              {!w.demo_role && (
                <button
                  disabled={!!busy}
                  className={`confirm-claim ${claim.confirmed ? 'confirmed' : ''}`}
                  onClick={() =>
                    run(
                      async () =>
                        updateWorkspace(
                          await api<Workspace>(`/workspaces/${w.id}/claims/${claim.id}`, 'PUT', {
                            confirmed: !claim.confirmed,
                          }),
                        ),
                      '保存事实确认…',
                    )
                  }
                >
                  <span className="checkbox">{claim.confirmed && <Check size={12} />}</span>
                  {claim.confirmed ? '已确认符合真实经历' : '我确认这段表达符合事实'}
                </button>
              )}
            </article>
          ))}
        </details>
      </Panel>
    </section>
  )
}

export { AgentInterview as Interview } from './agent-interview'

export function Review() {
  const { workspace, sessionId } = useWorkbench()
  const completed =
    workspace?.sessions
      .filter((s) => s.status !== 'active')
      .slice()
      .reverse() || []
  const selected = completed.find((s) => s.id === sessionId) || completed[0]
  return selected && selected.workflow_version !== 2 ? <LegacyReview /> : <AgentReview />
}

function LegacyReview() {
  const { workspace: w, sessionId, setSessionId, startInterview, busy, navigate } = useWorkbench()
  if (!w) return null
  const completed = w.sessions.filter((s) => s.status === 'completed').reverse()
  const s = completed.find((s) => s.id === sessionId) || completed[0]
  const r = s?.report
  return (
    <>
      <PageHeading
        eyebrow="REFLECT. REFINE. REPEAT."
        title="让这次练习，成为下次的进步。"
        description="只复盘已经回答的内容，不把未覆盖主题判定为薄弱。"
      >
        {s && (
          <>
            <a
              className="button secondary"
              href={`/api/workspaces/${w.id}/sessions/${s.id}/export`}
            >
              <Download size={15} />
              导出复盘
            </a>
            <Button
              disabled={
                !!busy || !r?.weak_topics.length || !w.analysis || s.analysis_id !== w.analysis.id
              }
              onClick={() => startInterview('weak', 12, s.id)}
            >
              <RefreshCw size={15} />
              复练薄弱主题
            </Button>
          </>
        )}
      </PageHeading>
      {!r || !s ? (
        <Panel title="练习后的收获会留在这里">
          <EmptyState
            title="还没有已完成的面试"
            description="完成一轮面试，或在回答后提前结束，就能生成复盘。"
            action="去模拟面试"
            onAction={() => navigate('interview')}
          />
        </Panel>
      ) : (
        <>
          <div className="review-selector">
            <span className="field-label">查看复盘</span>
            <select
              aria-label="选择复盘记录"
              value={s.id}
              onChange={(e) => setSessionId(e.target.value)}
            >
              {completed.map((item) => (
                <option key={item.id} value={item.id}>
                  {dateLabel(item.created_at)} ·{' '}
                  {item.focus === 'weak' ? '专项复练' : '项目经历面试'} · {item.turns.length} 题
                </option>
              ))}
            </select>
            <Badge>{s.mode === 'demo' ? '演示模式' : '真实模型'}</Badge>
          </div>
          <div className="review-summary">
            {(['supported', 'partial', 'unverified'] as const).map((status) => (
              <div className={`review-stat ${status}`} key={status}>
                <span>{verdictLabels[status]}</span>
                <strong>
                  {r.groups[status].length}
                  <small>次回答</small>
                </strong>
                <p>{[...new Set(r.groups[status])].join('、') || '本轮暂无'}</p>
              </div>
            ))}
          </div>
          <Notice>
            {r.demo_notice} {r.scope}
          </Notice>
          <Panel title="下一步行动" description="将反馈落实到事实补充、知识学习和表达练习。">
            {r.actions.length ? (
              <div className="actions-list">
                {r.actions.map((action, i) => (
                  <div key={action}>
                    <span className="step-index">{i + 1}</span>
                    <p>{action}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="inline-empty">
                <CheckCircle2 size={20} />
                <p>本轮已答问题暂无明确待补项，可换一个项目或场景继续练习。</p>
              </div>
            )}
          </Panel>
          <Panel
            title="逐题证据复盘"
            description={`已回答 ${r.answered} / 计划 ${r.planned} 题；次数包含追问，不是独立能力数量。`}
          >
            <div className="turns-list">
              {s.turns.map((turn, i) => (
                <details key={turn.request_id} className="turn-card" open={i === 0}>
                  <summary>
                    <span className="muted">{String(i + 1).padStart(2, '0')}</span>
                    <strong>{turn.question.topic}</strong>
                    <span className="turn-question-preview">{turn.question.text}</span>
                    <Badge status={turn.feedback!.verdict} />
                  </summary>
                  <div className="turn-body">
                    <h3>{turn.question.text}</h3>
                    <div className="row-between">
                      <span className="field-label">我的回答</span>
                      <span className="muted small">{dateLabel(turn.created_at)}</span>
                    </div>
                    <p className="preserve-lines">{turn.answer}</p>
                    <div className="turn-feedback-grid">
                      <div>
                        <h4>本题观察点</h4>
                        <ul>
                          {turn.question.criteria.map((t) => (
                            <li key={t}>{t}</li>
                          ))}
                        </ul>
                        <h4>回答证据</h4>
                        {turn.feedback!.answer_quotes.map((q) => (
                          <blockquote key={q}>{q}</blockquote>
                        ))}
                      </div>
                      <div>
                        <h4>需要补充</h4>
                        <ul>
                          {turn.feedback!.gaps.map((t) => (
                            <li key={t}>{t}</li>
                          ))}
                        </ul>
                        <h4>下一步</h4>
                        <p>{turn.feedback!.next_step}</p>
                      </div>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </Panel>
        </>
      )}
    </>
  )
}

export function ActivityPage() {
  const { workspace: w, run, busy } = useWorkbench()
  const [events, setEvents] = useState<RunEvent[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let ignore = false
    if (w)
      api<RunEvent[]>(`/workspaces/${w.id}/events?model_only=true`)
        .then((data) => {
          if (!ignore) setEvents(data)
        })
        .catch((e) => {
          if (!ignore) setError(e.message)
        })
    return () => {
      ignore = true
    }
  }, [w?.id, w?.revision])
  if (!w) return null
  const stage: Record<string, string> = {
    analysis: '经历与岗位证据分析',
    questions: '面试问题规划',
    feedback: '回答证据评估',
    interview: 'Agent 面试决策',
    judge: '独立模型评审',
    reference_answers: '复盘参考答案',
    demonstration_answer: '模型示范作答',
  }
  return (
    <>
      <PageHeading
        eyebrow="EVERY STEP, TRACEABLE"
        title="查看模型调用与消耗。"
        description="仅展示有 Token 消耗的模型调用；已发起但用量未知的请求保留标记。"
      >
        <Button
          disabled={!!busy}
          variant="secondary"
          onClick={() =>
            run(
              async () =>
                setEvents(await api<RunEvent[]>(`/workspaces/${w.id}/events?model_only=true`)),
              '刷新运行记录…',
            )
          }
        >
          <RefreshCw size={15} />
          刷新记录
        </Button>
      </PageHeading>
      {error && <Notice>{error}</Notice>}
      <div className="usage-summary" aria-label="最近运行 Token 用量">
        <strong>
          {events.some((e) => e.tokens != null)
            ? `${events.reduce((sum, e) => sum + (e.tokens || 0), 0).toLocaleString()} Token`
            : events.length
              ? '用量未知'
              : '暂无已返回用量'}
        </strong>
        <span>
          最近 100 条模型消耗记录的已返回用量，包含调用内的工具往返和格式修正；输出包含推理
          Token。缺失用量不估算。
        </span>
      </div>
      <Panel
        title="最近 100 条模型消耗记录"
        description="不展示只读工具、离线规则及未发出模型请求的检查。"
      >
        {!events.length ? (
          <EmptyState
            title="暂无模型消耗记录"
            description="使用真实模型分析、面试或复盘后，这里会显示消耗记录。"
          />
        ) : (
          <div className="events-table">
            <div className="events-head">
              <span>操作与模型</span>
              <span>总 Token</span>
              <span>耗时</span>
              <span>状态</span>
              <span>时间</span>
            </div>
            {events.map((e) => (
              <div className="event-row" key={e.id}>
                <div>
                  <strong>
                    {stage[e.stage] || e.stage}
                    {e.name ? ` · ${e.name}` : ''}
                  </strong>
                  <p>{e.model}</p>
                  <p className="token-usage">
                    {e.tokens == null
                      ? '用量未返回'
                      : `输入 ${e.input_tokens?.toLocaleString() ?? '—'} / 输出 ${e.output_tokens?.toLocaleString() ?? '—'}${e.usage_complete === false ? '（用量不完整）' : ''}`}
                  </p>
                  {!!e.repairs && <p className="muted small">结构修正 {e.repairs} 次</p>}
                  {e.finish_reason === 'length' && (
                    <p className="token-error">输出达到 Token 上限</p>
                  )}
                </div>
                <span>{e.tokens == null ? '未知' : e.tokens.toLocaleString()}</span>
                <span>
                  {e.duration_ms < 1000
                    ? `${e.duration_ms} ms`
                    : `${(e.duration_ms / 1000).toFixed(1)} s`}
                </span>
                <Badge status={e.status === 'success' ? 'supported' : 'unverified'}>
                  {e.status === 'success' ? '已返回' : '失败'}
                </Badge>
                <span className="muted small">{dateLabel(e.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  )
}

export function SettingsPage() {
  const { workspace, settings, mode, setMode, refreshSettings, run, busy } = useWorkbench()
  return (
    <>
      <PageHeading
        eyebrow="MAKE IT YOURS"
        title="选择适合你的准备方式。"
        description="先保存本机模型配置并验证工具调用。Agent 开发示范使用真实模型，全程记录调用用量。"
      >
        <Button
          variant="secondary"
          disabled={!!busy}
          onClick={() => run(refreshSettings, '检查模型配置…')}
        >
          <RefreshCw size={15} />
          检查配置
        </Button>
      </PageHeading>
      <div className="settings-grid">
        <Panel
          title="运行模式"
          description="切换仅影响新分析、新面试；进行中的面试沿用创建时的模式。"
        >
          {!workspace?.demo_role && (
            <button
              className={`mode-card ${mode === 'demo' ? 'active' : ''}`}
              onClick={() => setMode('demo')}
            >
              <span className="mode-icon">
                <Play size={20} />
              </span>
              <div>
                <strong>演示模式</strong>
                <p>固定规则和演示反馈，无需 Key 或外部服务。</p>
              </div>
              {mode === 'demo' && <CheckCircle2 size={19} />}
            </button>
          )}
          <button
            disabled={!settings?.configured}
            className={`mode-card ${mode === 'live' ? 'active' : ''}`}
            onClick={() => setMode('live')}
          >
            <span className="mode-icon">
              <Sparkles size={20} />
            </span>
            <div>
              <strong>真实模型</strong>
              <p>
                {settings?.configured
                  ? `当前模型：${settings.model}`
                  : '请在右侧填写并保存模型配置。'}
              </p>
            </div>
            {mode === 'live' && <CheckCircle2 size={19} />}
          </button>
          <Notice>真实模型请求失败会明确报错，本次结果不会保存，也不会自动切回演示模式。</Notice>
        </Panel>
        <ModelConfigPanel />
      </div>
      <Panel title="数据与事实边界">
        <div className="privacy-grid">
          <div>
            <ShieldCheck size={20} />
            <h3>本机保存</h3>
            <p>材料、记录保存在 SQLite。删除工作区会一并删除其记录与运行日志。</p>
          </div>
          <div>
            <FileText size={20} />
            <h3>明确原文依据</h3>
            <p>程序逐字核对引文；实际能力和技术正确性仍需人工确认。</p>
          </div>
          <div>
            <Activity size={20} />
            <h3>真实模式的数据流</h3>
            <p>
              分析时发送简历与
              JD，面试时按工具读取冻结材料和历史，评审时发送完整问答与评分标准到所配模型服务。
            </p>
          </div>
        </div>
      </Panel>
    </>
  )
}
