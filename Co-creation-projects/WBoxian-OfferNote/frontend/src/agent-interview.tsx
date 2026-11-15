import { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  Download,
  FileText,
  LoaderCircle,
  MessageSquareText,
  Play,
  RefreshCw,
  ShieldCheck,
  Target,
} from 'lucide-react'
import { api, dateLabel, streamDemonstrationAnswer } from './api'
import { Badge, Button, EmptyState, Notice, PageHeading, Panel } from './components'
import { useWorkbench } from './context'
import type { EvidenceRef, Session, Workspace } from './types'
import './agent-interview.css'

const closureLabels: Record<string, string> = {
  sufficient: '证据已足够',
  knowledge_boundary: '已触及能力边界',
  no_progress: '继续追问信息增益有限',
  budget: '达到本场预算',
  user_finish: '用户提前结束',
}

type DemonstrationDraft = { question_id: string; answer: string }
interface StreamingDraft {
  promise: Promise<DemonstrationDraft>
  text: string
  listeners: Set<(text: string) => void>
}
const demonstrationRequests = new Map<string, StreamingDraft>()

function demonstrationDraft(
  workspace: string,
  session: string,
  question: string,
  onText: (text: string) => void,
) {
  const path = `/workspaces/${workspace}/sessions/${session}/demonstration-answer/stream`
  const key = `${path}/${question}`
  let pending = demonstrationRequests.get(key)
  if (!pending) {
    const entry: StreamingDraft = {
      text: '',
      listeners: new Set(),
      promise: streamDemonstrationAnswer(path, question, (text) => {
        entry.text = text
        entry.listeners.forEach((listener) => listener(text))
      }).finally(() => demonstrationRequests.delete(key)),
    }
    pending = entry
    demonstrationRequests.set(key, pending)
  }
  pending.listeners.add(onText)
  if (pending.text) onText(pending.text)
  return { promise: pending.promise, unsubscribe: () => pending.listeners.delete(onText) }
}

function useReportPoll(session?: Session) {
  const { workspace, updateWorkspace } = useWorkbench()
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const id = workspace?.id
  const sid = session?.id
  const status = session?.status
  const reportError = session?.report_error
  useEffect(() => {
    setError('')
    if (!id || status !== 'awaiting_report' || reportError) return
    let ignore = false,
      fetching = false,
      attempts = 0
    const timer = window.setInterval(async () => {
      if (fetching) return
      if (++attempts > 240) {
        window.clearInterval(timer)
        setError('评审尚未返回。回答已保存，可以稍后刷新或重试评审。')
        return
      }
      fetching = true
      try {
        const next = await api<Workspace>(`/workspaces/${id}`)
        if (!ignore) {
          setError('')
          updateWorkspace(next)
        }
      } catch {
        if (!ignore) setError('暂时无法读取评审结果。回答已保存在本机，请检查后端服务。')
      } finally {
        fetching = false
      }
    }, 1500)
    return () => {
      ignore = true
      window.clearInterval(timer)
    }
    // updateWorkspace only writes the returned workspace; polling follows the stable identifiers.
  }, [id, sid, status, reportError, retry])
  return { error, restart: () => setRetry((value) => value + 1) }
}

function ReportPending({
  session,
  error,
  onRetry,
}: {
  session: Session
  error: string
  onRetry: () => void
}) {
  const { workspace: w, busy, run, updateWorkspace } = useWorkbench()
  const message = session.report_error || error
  return (
    <Panel title={message ? '评审尚未完成' : '正在生成独立评审与逐题参考答案'}>
      <div className="agent-pending">
        <span className="stat-icon violet">
          {message ? <FileText size={24} /> : <LoaderCircle className="spin" size={24} />}
        </span>
        <h2>{message ? '回答已保存，可以重试评审。' : '依据完整问答，逐项核对评分证据。'}</h2>
        <p>
          {message ||
            '完成后会自动显示评分、优缺点、改进计划和逐题参考答案。按批生成参考答案可能需要几分钟，你可以离开页面，稍后回来查看。'}
        </p>
        <Button
          variant="secondary"
          disabled={!!busy}
          onClick={() =>
            run(async () => {
              updateWorkspace(
                await api<Workspace>(`/workspaces/${w!.id}/sessions/${session.id}/finish`, 'POST'),
              )
              onRetry()
            }, '正在重新启动独立评审…')
          }
        >
          <RefreshCw size={16} />
          重试评审
        </Button>
      </div>
    </Panel>
  )
}

export function AgentInterview() {
  const {
    workspace: w,
    busy,
    run,
    updateWorkspace,
    startInterview,
    sessionId,
    setSessionId,
    navigate,
    setUnsaved,
  } = useWorkbench()
  const [answer, setAnswer] = useState('')
  const [count, setCount] = useState(w?.demo_role === 'development' ? 4 : 12)
  const [generating, setGenerating] = useState(false)
  const [generationError, setGenerationError] = useState('')
  const [generationRetry, setGenerationRetry] = useState(0)
  const attemptedQuestion = useRef('')
  const readyQuestion = useRef('')
  const editor = useRef<HTMLTextAreaElement>(null)
  const followOutput = useRef(true)
  const [maxTopic, setMaxTopic] = useState(6)
  const request = useRef({ question: '', answer: '', id: '' })
  const s =
    w?.sessions.find((x) => x.id === sessionId) ||
    w?.sessions
      .slice()
      .reverse()
      .find((x) => x.status === 'active' && x.workflow_version === 2)
  const question = s?.questions[s.turns.length]
  const isDemonstration =
    !!s &&
    (s.demonstration ||
      (w?.demo_role === 'development' &&
        s.mode === 'live' &&
        s.workflow_version === 2 &&
        s.status === 'active'))
  const poll = useReportPoll(s)
  useEffect(() => {
    setAnswer('')
    readyQuestion.current = ''
    followOutput.current = true
    setGenerationError('')
    setGenerating(false)
  }, [s?.id, question?.id])
  useEffect(() => {
    if (!isDemonstration || !w || !s || !question || busy) return
    const key = `${w.id}/${s.id}/${question.id}/${generationRetry}`
    if (attemptedQuestion.current === key) return
    attemptedQuestion.current = key
    let ignore = false
    setGenerating(true)
    setGenerationError('')
    setAnswer('')
    readyQuestion.current = ''
    const stream = demonstrationDraft(w.id, s.id, question.id, (text) => {
      if (!ignore) setAnswer(text)
    })
    stream.promise
      .then((draft) => {
        if (!ignore && draft.question_id === question.id) {
          readyQuestion.current = question.id
          setAnswer(draft.answer)
        }
      })
      .catch((error) => {
        if (!ignore)
          setGenerationError(error instanceof Error ? error.message : '示范回答生成失败，请重试。')
      })
      .finally(() => {
        if (!ignore) setGenerating(false)
      })
    return () => {
      ignore = true
      stream.unsubscribe()
      if (attemptedQuestion.current === key) attemptedQuestion.current = ''
    }
  }, [w?.id, s?.id, question?.id, isDemonstration, busy, generationRetry])
  useEffect(() => {
    setUnsaved(!!answer.trim() && !isDemonstration)
    return () => setUnsaved(false)
  }, [answer, isDemonstration, setUnsaved])
  useEffect(() => {
    if (generating && followOutput.current && editor.current)
      editor.current.scrollTop = editor.current.scrollHeight
  }, [answer, generating])
  if (!w) return null
  const leaveDraft = () =>
    isDemonstration || !answer.trim() || window.confirm('回答尚未提交，确定放弃这段草稿？')
  async function submit() {
    if (
      !s ||
      !question ||
      generating ||
      generationError ||
      (isDemonstration && readyQuestion.current !== question.id)
    )
      return
    if (request.current.question !== question.id || request.current.answer !== answer)
      request.current = {
        question: question.id,
        answer,
        id: crypto.randomUUID(),
      }
    await run(async () => {
      updateWorkspace(
        await api<Workspace>(`/workspaces/${w!.id}/sessions/${s.id}/answers`, 'POST', {
          answer,
          question_id: question.id,
          request_id: request.current.id,
        }),
      )
      setAnswer('')
      setUnsaved(false)
    }, '面试官正在核对证据并决定下一问…')
  }
  return (
    <>
      <PageHeading
        eyebrow="FOLLOW THE EVIDENCE"
        title="把经历，一层层讲清楚。"
        description="同一主题持续深挖，摸清证据与能力边界后再换题。评分在面试结束后统一展示。"
      >
        <select
          className="compact-select"
          aria-label="选择面试记录"
          value={s?.id || ''}
          onChange={(e) => {
            if (leaveDraft()) {
              setAnswer('')
              setUnsaved(false)
              setSessionId(e.target.value)
            } else e.target.value = s?.id || ''
          }}
        >
          <option value="">选择面试记录</option>
          {w.sessions
            .slice()
            .reverse()
            .map((x) => (
              <option key={x.id} value={x.id}>
                {dateLabel(x.created_at)} ·{' '}
                {x.status === 'active'
                  ? '进行中'
                  : x.status === 'awaiting_report'
                    ? '评审中'
                    : '已完成'}
                {x.workflow_version !== 2 ? ' · 旧版' : ''}
              </option>
            ))}
        </select>
        <Button
          variant="secondary"
          disabled={!!busy || !w.analysis}
          onClick={() => {
            if (leaveDraft()) startInterview('all', count, undefined, maxTopic)
          }}
        >
          <Play size={15} />
          新一轮面试
        </Button>
      </PageHeading>
      {w.demo_role === 'development' && !s && (
        <Panel
          title="真实模型示范 · Agent 开发"
          description="虚构材料，模型示范作答；阅读后逐轮提交，最后体验真实评分与复盘。"
        >
          <Button disabled={!!busy} onClick={() => startInterview('all', 4, undefined, 3, true)}>
            <Play size={16} />
            开始真实示范（4轮）
          </Button>
        </Panel>
      )}
      {isDemonstration && (
        <Notice>
          这是一场模型示范面试，不评价你的能力。进入每题后自动生成示范回答，阅读后点击提交；问题、回答和复盘均来自真实模型调用，不保证固定分数。
        </Notice>
      )}
      {!s ? (
        <div className="interview-start panel">
          <div className="start-illustration">
            <MessageSquareText size={34} />
            <span>01</span>
          </div>
          <span className="eyebrow">ADAPTIVE INTERVIEW</span>
          <h2>问到细节，也尊重真实边界。</h2>
          <p>
            问题由你的回答推动。面试官会核对材料、回看同一主题的历史，再决定继续深挖或切换主题。
          </p>
          <div className="interview-options">
            <label>
              整场题目预算
              <select
                aria-label="面试题目数量"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              >
                {[4, 8, 12, 18, 24].map((n) => (
                  <option key={n} value={n}>
                    {n} 轮（含追问）
                  </option>
                ))}
              </select>
            </label>
            <label>
              单主题上限
              <select
                aria-label="单主题追问上限"
                value={maxTopic}
                onChange={(e) => setMaxTopic(Number(e.target.value))}
              >
                {[3, 4, 6, 8].map((n) => (
                  <option key={n} value={n}>
                    {n} 轮
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Button
            disabled={!!busy || !w.analysis}
            onClick={() => startInterview('all', count, undefined, maxTopic)}
          >
            <Play size={16} />
            开始本轮面试
          </Button>
          {!w.analysis && <p>请先保存材料并完成证据分析。</p>}
        </div>
      ) : s.status === 'awaiting_report' ? (
        <ReportPending session={s} error={poll.error} onRetry={poll.restart} />
      ) : s.status === 'completed' ? (
        <Panel title="这一轮面试已结束">
          <EmptyState
            title="把问答变成有依据的复盘"
            description="查看维度评分、优缺点和改进计划，或选择需要复练的主题。"
            action="查看本轮复盘"
            onAction={() => {
              setSessionId(s.id)
              navigate('review')
            }}
          />
        </Panel>
      ) : s.workflow_version !== 2 ? (
        <Panel title="旧版面试记录已保留">
          <Notice>旧版面试沿用原始数据，不转换或覆盖历史问题。请结束后新建 Agent 面试。</Notice>
          <Button
            disabled={!!busy || !s.turns.length}
            onClick={() =>
              run(
                async () =>
                  updateWorkspace(
                    await api<Workspace>(`/workspaces/${w.id}/sessions/${s.id}/finish`, 'POST'),
                  ),
                '正在保存旧版复盘…',
              )
            }
          >
            结束旧版面试
          </Button>
        </Panel>
      ) : (
        <>
          <div className="interview-progress">
            <span>
              第 {s.turns.length + 1} 轮 · 整场上限 {s.budget?.total_turns} 轮
            </span>
            <div>
              <span
                style={{
                  width: `${(s.turns.length / (s.budget?.total_turns || 12)) * 100}%`,
                }}
              />
            </div>
            <Badge>{s.mode === 'demo' ? '离线演示' : '真实 Agent'}</Badge>
          </div>
          <div className="interview-grid">
            <Panel
              title={
                question?.follow_up_depth
                  ? `当前主题 · 深挖第 ${question.follow_up_depth + 1} 轮`
                  : '进入一个新的主题'
              }
              action={<span className="topic-label">{question?.topic}</span>}
            >
              <div className="interviewer-label">
                <span className="interviewer-avatar">N</span>
                <div>
                  <strong>OfferNote 面试官</strong>
                  <span>依据你的回答，决定下一步</span>
                </div>
              </div>
              <h2 className="question-text">{question?.text}</h2>
              <label className="field-label" htmlFor="answer">
                {isDemonstration ? '示范候选人的回答' : '你的回答'}
              </label>
              <textarea
                id="answer"
                ref={editor}
                onScroll={(event) => {
                  const element = event.currentTarget
                  followOutput.current =
                    element.scrollHeight - element.scrollTop - element.clientHeight < 48
                }}
                className="answer-editor"
                maxLength={6000}
                value={answer}
                readOnly={isDemonstration}
                onChange={(e) => setAnswer(e.target.value)}
                disabled={!!busy}
                placeholder={
                  isDemonstration
                    ? '模型正在自动生成示范回答…'
                    : '请基于真实经历作答。不清楚的部分可以直接说明。'
                }
              />
              {generationError && (
                <div role="alert">
                  <Notice>{generationError}</Notice>
                </div>
              )}
              <div className="answer-toolbar">
                <span className="muted small">{answer.length} / 6,000 字符</span>
                {generating && (
                  <span role="status">
                    <LoaderCircle className="spin" size={16} />
                    {answer ? '正在流式输出…' : '等待模型首段输出…'}
                  </span>
                )}
                {generationError && (
                  <Button
                    variant="secondary"
                    disabled={!!busy || generating}
                    onClick={() => setGenerationRetry((value) => value + 1)}
                  >
                    重试生成示范回答
                  </Button>
                )}
                <Button
                  disabled={
                    !!busy ||
                    generating ||
                    !!generationError ||
                    !answer.trim() ||
                    (isDemonstration && readyQuestion.current !== question?.id)
                  }
                  onClick={submit}
                >
                  {isDemonstration ? '提交并查看追问' : '提交回答'}
                  <ArrowRight size={16} />
                </Button>
              </div>
              <button
                className="finish-button"
                disabled={!!busy || !s.turns.length}
                onClick={() => {
                  if (!leaveDraft()) return
                  run(async () => {
                    updateWorkspace(
                      await api<Workspace>(`/workspaces/${w.id}/sessions/${s.id}/finish`, 'POST'),
                    )
                    setAnswer('')
                    setUnsaved(false)
                    navigate('review')
                  }, '正在保存面试并启动独立评审…')
                }}
              >
                提前结束，评审已答部分
              </button>
            </Panel>
            <Panel title="本场主题" description="达到证据目标、能力边界或轮次上限后切换。">
              <div className="agent-topic-list">
                {s.topics?.map((t) => (
                  <div key={t.id} className={`agent-topic ${t.status}`}>
                    <span>{t.status === 'closed' ? '✓' : t.status === 'active' ? '•' : '○'}</span>
                    <div>
                      <strong>{t.title}</strong>
                      <small>
                        {t.status === 'closed'
                          ? '已结束'
                          : t.status === 'active'
                            ? '正在深入'
                            : '待覆盖'}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
              <div className="agent-side-note">
                <ShieldCheck size={18} />
                <p>面试过程中保留原始问答，评分和具体改进建议在结束后展示。</p>
              </div>
              {s.mode === 'demo' && (
                <Notice>
                  演示使用固定追问规则，用于体验流程，不代表真实 Agent 决策或能力评估。
                </Notice>
              )}
            </Panel>
          </div>
          {!!s.turns.length && (
            <Panel title="本场已提交的回答">
              <Transcript session={s} />
            </Panel>
          )}
        </>
      )}
    </>
  )
}

function Evidence({ references, session }: { references: EvidenceRef[]; session: Session }) {
  return (
    <div className="agent-evidence">
      {references.map((ref, i) => {
        const index = session.turns.findIndex((t) => t.id === ref.turn_id)
        return (
          <blockquote key={`${ref.turn_id}-${i}`}>
            <a
              href={`#turn-${ref.turn_id}`}
              onClick={() =>
                document.getElementById(`turn-${ref.turn_id}`)?.setAttribute('open', '')
              }
            >
              第 {index + 1} 题原文
            </a>
            <p>{ref.quote}</p>
          </blockquote>
        )
      })}
    </div>
  )
}

function Transcript({ session }: { session: Session }) {
  return (
    <div className="turns-list">
      {session.turns.map((turn, i) => (
        <details
          id={`turn-${turn.id || turn.request_id}`}
          key={turn.request_id}
          className="turn-card"
        >
          <summary>
            <span className="muted">{String(i + 1).padStart(2, '0')}</span>
            <strong>{turn.question.topic}</strong>
            <span className="turn-question-preview">{turn.question.text}</span>
          </summary>
          <div className="turn-body">
            <h3>{turn.question.text}</h3>
            {session.demonstration && (
              <Badge>
                {turn.answer_source === 'model_demonstration'
                  ? '模型示范回答'
                  : turn.answer_source === 'edited_demonstration'
                    ? '编辑后的示范回答'
                    : '用户提交的回答'}
              </Badge>
            )}
            <p className="preserve-lines">{turn.answer}</p>
            {session.report?.reference_answers
              ?.filter((a) => a.turn_id === turn.id)
              .map((a) => (
                <section className="reference-answer" key={a.turn_id}>
                  <h3>模型参考答案</h3>
                  <p className="muted small">
                    学习示范，技术结论需核对；个人贡献和项目数字请结合真实经历补充。
                  </p>
                  <p className="preserve-lines">{a.answer}</p>
                  <strong>回答要点</strong>
                  <ul>
                    {a.key_points.map((point, index) => (
                      <li key={index}>{point}</li>
                    ))}
                  </ul>
                  {!!a.pitfalls.length && (
                    <>
                      <strong>常见误区</strong>
                      <ul>
                        {a.pitfalls.map((point, index) => (
                          <li key={index}>{point}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </section>
              ))}
            <span className="muted small">{dateLabel(turn.created_at)}</span>
          </div>
        </details>
      ))}
    </div>
  )
}

export function AgentReview() {
  const {
    workspace: w,
    sessionId,
    setSessionId,
    startInterview,
    busy,
    navigate,
    run,
    updateWorkspace,
  } = useWorkbench()
  const available =
    w?.sessions
      .filter((s) => s.status !== 'active')
      .slice()
      .reverse() || []
  const s = available.find((s) => s.id === sessionId) || available[0]
  const poll = useReportPoll(s)
  if (!w) return null
  const r = s?.report
  return (
    <>
      <PageHeading
        eyebrow="EVIDENCE. REFLECTION. NEXT STEP."
        title="让每一分，都有回答作依据。"
        description="独立评审依据实际问答评分。未覆盖项保留为未评估，优缺点与建议关联原文。"
      >
        {s?.status === 'completed' && r && (
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
                !!busy || !r.weak_topics.length || !w.analysis || s.analysis_id !== w.analysis.id
              }
              onClick={() => startInterview('weak', 12, s.id)}
            >
              <RefreshCw size={15} />
              {s.mode === 'demo' ? '体验主题复练' : '复练待提升主题'}
            </Button>
          </>
        )}
      </PageHeading>
      {!!available.length && (
        <div className="review-selector">
          <span className="field-label">查看复盘</span>
          <select
            aria-label="选择复盘记录"
            value={s?.id || ''}
            onChange={(e) => setSessionId(e.target.value)}
          >
            {available.map((x) => (
              <option key={x.id} value={x.id}>
                {dateLabel(x.created_at)} · {x.status === 'awaiting_report' ? '评审中' : '已完成'} ·{' '}
                {x.turns.length} 轮
              </option>
            ))}
          </select>
          <Badge>{s?.mode === 'demo' ? '离线演示' : '真实模型'}</Badge>
        </div>
      )}
      {!s ? (
        <Panel title="复盘会留在这里">
          <EmptyState
            title="还没有已结束的面试"
            description="完成一轮逐题面试，再查看有依据的反馈。"
            action="去模拟面试"
            onAction={() => navigate('interview')}
          />
        </Panel>
      ) : s.status === 'awaiting_report' ? (
        <ReportPending session={s} error={poll.error} onRetry={poll.restart} />
      ) : !r ? (
        <Notice>本场尚未形成评审报告。</Notice>
      ) : (
        <>
          <section className="agent-score-hero">
            <div>
              <span className="eyebrow">
                {s.mode === 'demo' ? 'DEMO · NO SCORE' : 'INTERVIEW REVIEW'}
              </span>
              <h2>
                {s.mode === 'demo'
                  ? '演示流程已完成'
                  : r.total_score == null
                    ? '尚未形成有效综合分'
                    : '本场参考综合分'}
              </h2>
              <p>{r.summary}</p>
              <span className="muted small">
                已回答 {r.answered} 轮 · 评分契约 {r.rubric_version}
              </span>
            </div>
            <div className="agent-total">
              <strong>{r.total_score ?? '—'}</strong>
              <span>/ 100</span>
              <p>已评估权重 {r.covered_weight ?? 0}%</p>
            </div>
          </section>
          <Notice>
            {s.demonstration && '模型示范面试：虚构材料与示范作答，不评价使用者本人能力。'}{' '}
            {r.demo_notice} {r.scope} 已评估权重不足 60% 时不显示综合分。
          </Notice>
          {r.warnings?.map((t) => (
            <Notice key={t}>{t}</Notice>
          ))}
          <div className="agent-dimension-grid">
            {r.scores?.map((score) => (
              <article className="panel agent-dimension" key={score.dimension}>
                <div className="row-between">
                  <h3>{score.label}</h3>
                  <span className="muted small">权重 {score.weight}%</span>
                </div>
                <strong>
                  {score.score ?? '—'}
                  <small>{score.score == null ? '未评估' : '/ 4'}</small>
                </strong>
                <div className={`agent-score-bar ${score.score == null ? 'empty' : ''}`}>
                  <span style={{ width: `${((score.score ?? 0) / 4) * 100}%` }} />
                </div>
                <p>{score.reason}</p>
                <Evidence references={score.evidence} session={s} />
              </article>
            ))}
          </div>
          <div className="agent-findings-grid">
            {[
              {
                title: '本场表现出的优点',
                items: r.strengths || [],
                empty: '本场尚无带有效回答证据的优点判断。',
                icon: ShieldCheck,
              },
              {
                title: '需要改进的部分',
                items: r.weaknesses || [],
                empty: '本场尚无带有效回答证据的薄弱点判断。',
                icon: Target,
              },
            ].map((group) => (
              <Panel key={group.title} title={group.title}>
                <div className="agent-findings">
                  {!group.items.length ? (
                    <p className="muted">{group.empty}</p>
                  ) : (
                    group.items.map((finding, i) => (
                      <article key={i}>
                        <h3>
                          <group.icon size={16} />
                          {finding.text}
                        </h3>
                        <Evidence references={finding.evidence} session={s} />
                      </article>
                    ))
                  )}
                </div>
              </Panel>
            ))}
          </div>
          <Panel title="下一步改进计划" description="按优先级练习，再用新一轮面试检查进步。">
            <div className="agent-improvements">
              {!r.improvements?.length ? (
                <p className="muted">本场暂无通过证据校验的具体改进计划。</p>
              ) : (
                r.improvements.map((item, i) => (
                  <article key={i}>
                    <div className="row-between">
                      <h3>
                        {i + 1}. {item.title}
                      </h3>
                      <Badge>
                        {
                          {
                            high: '优先处理',
                            medium: '继续练习',
                            low: '进一步完善',
                          }[item.priority]
                        }
                      </Badge>
                    </div>
                    <p>{item.detail}</p>
                    <div className="agent-exercise">
                      <strong>练习与验证</strong>
                      <p>{item.exercise}</p>
                    </div>
                    <Evidence references={item.evidence} session={s} />
                  </article>
                ))
              )}
            </div>
          </Panel>
          <Panel title="主题覆盖与结束依据" description="未作答的主题不参与评分。">
            <div className="agent-topic-report">
              {s.topics?.map((topic) => {
                const score = r.topics?.find((x) => x.topic_id === topic.id)
                return (
                  <article key={topic.id}>
                    <div className="row-between">
                      <h3>{topic.title}</h3>
                      <Badge>{score?.score == null ? '未评估' : `${score.score} / 4`}</Badge>
                    </div>
                    <p>{score?.reason || '未覆盖到该主题，不作为能力判断。'}</p>
                    <span className="muted small">
                      {topic.closure ? closureLabels[topic.closure] || topic.closure : '本场未覆盖'}
                      {topic.reason && ` · ${topic.reason}`}
                    </span>
                    {score && <Evidence references={score.evidence} session={s} />}
                  </article>
                )
              })}
            </div>
          </Panel>
          <Panel
            title="逐题复盘与参考答案"
            description="展开每道问题，对照原始回答、模型参考答案、回答要点与常见误区。"
          >
            {s.mode === 'live' && (!r.reference_answers?.length || r.reference_answers_error) && (
              <div className="reference-retry">
                <p className="muted">
                  {r.reference_answers_error || '这份历史报告尚未生成参考答案。'}
                </p>
                <Button
                  disabled={!!busy}
                  onClick={() =>
                    run(
                      async () =>
                        updateWorkspace(
                          await api<Workspace>(
                            `/workspaces/${w.id}/sessions/${s.id}/reference-answers`,
                            'POST',
                          ),
                        ),
                      '正在逐题生成参考答案…',
                    )
                  }
                >
                  生成参考答案
                </Button>
              </div>
            )}
            {s.mode === 'demo' && (
              <p className="muted">演示模式保留问答记录；真实模型模式会生成逐题参考答案。</p>
            )}
            <Transcript session={s} />
          </Panel>
          <Panel
            title="面试决策记录"
            description="记录动作、简短理由与工具结果状态，不展示隐含思考过程。"
          >
            <div className="agent-decision-list">
              {s.trace?.map((entry, i) => (
                <article key={i}>
                  <span className="step-index">{i + 1}</span>
                  <div>
                    <strong>
                      {
                        {
                          ask_followup: '继续深挖',
                          switch_topic: '进入新主题',
                          finish: '结束面试',
                        }[entry.action]
                      }
                    </strong>
                    <p>{entry.reason}</p>
                    <span className="muted small">
                      {entry.tools
                        .map((t) => `${t.name} · ${t.status === 'success' ? '成功' : '失败'}`)
                        .join(' / ') || '本次未调用工具'}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </Panel>
        </>
      )}
    </>
  )
}
