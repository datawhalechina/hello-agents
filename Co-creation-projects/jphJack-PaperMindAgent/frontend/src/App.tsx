// Paper Innovation Agent - 主应用组件
// 状态管理 + 布局 + 交互流程
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { deletePaper, getHealth, getReport, listPapers, startAnalysis, subscribeProgress, uploadPaper } from './api'
import { STAGE_LIST } from './types'
import type { AnalyzeParams, Evaluation, Paper, ProgressEvent, Report, StageKey } from './types'
import ProgressBar from './components/ProgressBar'
import StepsTimeline from './components/StepsTimeline'
import EvaluationPanel from './components/EvaluationPanel'
import ReportView from './components/ReportView'
import PaperLibrary from './components/PaperLibrary'

/** 初始化：所有阶段事件为空 */
function createEmptyEvents(): Record<StageKey, ProgressEvent | undefined> {
  const obj = {} as Record<StageKey, ProgressEvent | undefined>
  STAGE_LIST.forEach((s) => (obj[s.key] = undefined))
  return obj
}

type TabKey = 'report' | 'evaluation'

export default function App() {
  // 输入与任务状态
  const [folderPath, setFolderPath] = useState('')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [running, setRunning] = useState(false)

  // 输入模式：上传论文 / 文件夹路径
  const [inputMode, setInputMode] = useState<'upload' | 'folder'>('upload')
  // 论文库列表与选中状态
  const [papers, setPapers] = useState<Paper[]>([])
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set())
  // 研究方向（注入创新点生成提示词）
  const [researchDirection, setResearchDirection] = useState('')
  // 上传中状态
  const [uploading, setUploading] = useState(false)

  // 进度与报告
  const [eventsByStage, setEventsByStage] = useState<Record<StageKey, ProgressEvent | undefined>>(
    createEmptyEvents,
  )
  const [overallProgress, setOverallProgress] = useState(0)
  const [report, setReport] = useState<Report | null>(null)
  const [reportLoading, setReportLoading] = useState(false)

  // 错误与健康检查
  const [error, setError] = useState<string | null>(null)
  const [model, setModel] = useState<string>('deepseek-chat')
  const [healthOk, setHealthOk] = useState<boolean>(true)

  // Tab 切换
  const [activeTab, setActiveTab] = useState<TabKey>('report')

  // EventSource 引用，便于卸载/重试时关闭
  const sourceRef = useRef<EventSource | null>(null)

  /** 关闭当前 SSE 订阅 */
  const closeSource = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
  }, [])

  /** 拉取论文库列表 */
  const refreshPapers = useCallback(async () => {
    try {
      const { papers } = await listPapers()
      setPapers(papers)
    } catch (err) {
      console.warn('拉取论文库失败:', err)
    }
  }, [])

  /** 上传 PDF 论文 */
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    try {
      await uploadPaper(file)
      await refreshPapers()
    } catch (err) {
      setError(`上传失败: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setUploading(false)
    }
  }, [refreshPapers])

  /** 删除论文 */
  const handleDeletePaper = useCallback(async (paperId: string) => {
    try {
      await deletePaper(paperId)
      setSelectedPaperIds((prev) => {
        const next = new Set(prev)
        next.delete(paperId)
        return next
      })
      await refreshPapers()
    } catch (err) {
      setError(`删除失败: ${err instanceof Error ? err.message : String(err)}`)
    }
  }, [refreshPapers])

  /** 切换论文选中状态 */
  const handleToggleSelect = useCallback((paperId: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev)
      if (next.has(paperId)) next.delete(paperId)
      else next.add(paperId)
      return next
    })
  }, [])

  /** 健康检查：拉取后端模型信息 */
  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((info) => {
        if (cancelled) return
        setModel(info.model || 'deepseek-chat')
        setHealthOk(info.status === 'ok')
      })
      .catch(() => {
        if (!cancelled) setHealthOk(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /** 挂载时拉取论文库 */
  useEffect(() => {
    void refreshPapers()
  }, [refreshPapers])

  /** 卸载时关闭 SSE */
  useEffect(() => {
    return () => closeSource()
  }, [closeSource])

  /** 拉取最终报告 */
  const fetchReport = useCallback(async (id: string) => {
    setReportLoading(true)
    try {
      const r = await getReport(id)
      setReport(r)
      // 自动切到报告 Tab
      setActiveTab('report')
    } catch (err) {
      setError(`获取报告失败: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setReportLoading(false)
    }
  }, [])

  /** 启动分析 */
  const handleStart = useCallback(async () => {
    // 根据输入模式构建请求参数
    const params: AnalyzeParams = {}
    if (inputMode === 'folder') {
      const path = folderPath.trim()
      if (!path) {
        setError('请输入 PDF 文件夹路径')
        return
      }
      params.folder_path = path
    } else {
      if (selectedPaperIds.size === 0) {
        setError('请至少选择一篇论文')
        return
      }
      params.paper_ids = Array.from(selectedPaperIds)
    }
    const direction = researchDirection.trim()
    if (direction) params.research_direction = direction

    setError(null)
    setStarting(true)
    setRunning(true)
    setReport(null)
    setOverallProgress(0)
    setEventsByStage(createEmptyEvents())

    // 关闭可能存在的旧订阅
    closeSource()

    try {
      const { task_id } = await startAnalysis(params)
      setTaskId(task_id)

      // 订阅进度
      const source = subscribeProgress(
        task_id,
        (evt: ProgressEvent) => {
          setEventsByStage((prev) => ({ ...prev, [evt.stage]: evt }))
          if (typeof evt.progress === 'number' && Number.isFinite(evt.progress)) {
            setOverallProgress(evt.progress)
          }
          // 任意步骤失败：标记错误但继续监听
          if (evt.status === 'failed') {
            setError(`步骤 ${evt.stage} 失败: ${evt.message}`)
          }
        },
        () => {
          // step7_integrate done
          setRunning(false)
          setOverallProgress(1)
          void fetchReport(task_id)
        },
        () => {
          // SSE 错误：若任务尚未完成，提示连接异常
          setRunning((r) => {
            if (r) {
              setError('进度订阅连接异常，可点击重试恢复')
            }
            return r
          })
        },
      )
      sourceRef.current = source
    } catch (err) {
      setError(`启动分析失败: ${err instanceof Error ? err.message : String(err)}`)
      setRunning(false)
    } finally {
      setStarting(false)
    }
  }, [inputMode, folderPath, selectedPaperIds, researchDirection, closeSource, fetchReport])

  /** 重试：基于已有 taskId 重新订阅 + 拉报告 */
  const handleRetry = useCallback(async () => {
    if (!taskId) {
      void handleStart()
      return
    }
    setError(null)
    setRunning(true)
    closeSource()
    try {
      const source = subscribeProgress(
        taskId,
        (evt: ProgressEvent) => {
          setEventsByStage((prev) => ({ ...prev, [evt.stage]: evt }))
          if (typeof evt.progress === 'number' && Number.isFinite(evt.progress)) {
            setOverallProgress(evt.progress)
          }
        },
        () => {
          setRunning(false)
          setOverallProgress(1)
          void fetchReport(taskId)
        },
      )
      sourceRef.current = source
    } catch (err) {
      setError(`重试失败: ${err instanceof Error ? err.message : String(err)}`)
      setRunning(false)
    }
  }, [taskId, closeSource, fetchReport, handleStart])

  /** 评估数据：优先取 report.evaluation，其次 report.report.evaluation */
  const evaluation: Evaluation | null = useMemo(() => {
    if (!report) return null
    return report.evaluation ?? report.report?.evaluation ?? null
  }, [report])

  /** Markdown 文本 */
  const markdown = useMemo(() => report?.markdown ?? report?.report?.markdown ?? '', [report])

  /** 是否有任意步骤处于运行/完成态（用于判断时间线是否激活） */
  const hasActivity = useMemo(
    () => Object.values(eventsByStage).some((e) => e !== undefined),
    [eventsByStage],
  )

  return (
    <div className="app">
      {/* 顶部标题栏 */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-logo" aria-hidden>P</div>
          <div>
            <div className="brand-title">Paper Innovation Agent</div>
            <div className="brand-subtitle">七步漏斗式论文创新点生成系统</div>
          </div>
        </div>
        <div className="header-right">
          <span className="model-badge">
            <span className={`dot ${healthOk ? '' : 'offline'}`} />
            {healthOk ? '服务正常' : '服务离线'} · {model}
          </span>
        </div>
      </header>

      <div className="app-body">
        {/* 左侧输入区 + 进度 + 时间线 */}
        <aside className="sidebar">
          <div className="input-card">
            <h3 className="card-title">分析输入</h3>

            {/* 输入模式切换 */}
            <div className="mode-toggle">
              <button
                className={`mode-btn ${inputMode === 'upload' ? 'active' : ''}`}
                onClick={() => setInputMode('upload')}
                disabled={starting || running}
              >
                上传论文
              </button>
              <button
                className={`mode-btn ${inputMode === 'folder' ? 'active' : ''}`}
                onClick={() => setInputMode('folder')}
                disabled={starting || running}
              >
                文件夹路径
              </button>
            </div>

            {/* 上传模式：论文库；文件夹模式：路径输入 */}
            {inputMode === 'upload' ? (
              <PaperLibrary
                papers={papers}
                selectedIds={selectedPaperIds}
                onToggleSelect={handleToggleSelect}
                onDelete={handleDeletePaper}
                onUpload={handleUpload}
                uploading={uploading}
                disabled={starting || running}
              />
            ) : (
              <>
                <input
                  className="path-input"
                  type="text"
                  placeholder="例如：D:/papers 或 /home/user/papers"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !starting && !running) {
                      void handleStart()
                    }
                  }}
                  disabled={starting || running}
                  aria-label="PDF 文件夹路径"
                />
                <p className="hint">输入包含 PDF 论文的本地文件夹路径，系统将自动解析并生成创新点。</p>
              </>
            )}

            {/* 研究方向（两种模式都显示） */}
            <div className="research-direction">
              <label className="research-label" htmlFor="research-direction">
                研究方向（可选）
              </label>
              <input
                id="research-direction"
                className="path-input"
                type="text"
                placeholder="例如：大模型高效微调、多模态推理"
                value={researchDirection}
                onChange={(e) => setResearchDirection(e.target.value)}
                disabled={starting || running}
                aria-label="研究方向"
              />
              <p className="hint">注入到创新点生成提示词，引导生成与方向相关的创新点。</p>
            </div>

            <button
              className="btn btn-primary"
              onClick={() => void handleStart()}
              disabled={
                starting ||
                running ||
                (inputMode === 'folder' ? !folderPath.trim() : selectedPaperIds.size === 0)
              }
            >
              {starting ? <><span className="spinner" /> 启动中...</> : running ? '分析进行中' : '启动分析'}
            </button>
          </div>

          {/* 整体进度条 */}
          {(hasActivity || running) && (
            <ProgressBar progress={overallProgress} active={running} />
          )}

          {/* 七步时间线 */}
          <div>
            <div className="section-divider">执行链路</div>
            <StepsTimeline eventsByStage={eventsByStage} />
          </div>

          {/* 错误提示 + 重试 */}
          {error && (
            <div className="error-banner">
              <span className="error-icon" aria-hidden>!</span>
              <span className="error-text">{error}</span>
              <div className="error-actions">
                <button className="btn btn-secondary" onClick={() => void handleRetry()} disabled={starting}>
                  重试
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* 右侧主内容区：Tab 切换 */}
        <main className="main-content">
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'report' ? 'active' : ''}`}
              onClick={() => setActiveTab('report')}
            >
              研究报告
            </button>
            <button
              className={`tab ${activeTab === 'evaluation' ? 'active' : ''}`}
              onClick={() => setActiveTab('evaluation')}
            >
              评估指标
              {evaluation ? <span className="badge">{evaluation.innovations_scores?.length ?? 0}</span> : null}
            </button>
          </div>

          <div className="report-container">
            {activeTab === 'report' ? (
              <ReportView markdown={markdown} loading={reportLoading} />
            ) : (
              <EvaluationPanel evaluation={evaluation} />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
