// 评估指标面板：工具调用成功率 / 总数 / 失败数 / 平均置信度 / 三维评分
import type { Evaluation, ThreeDScore } from '../types'

interface EvaluationPanelProps {
  evaluation: Evaluation | null
}

/** 0-1 比率转百分比字符串 */
function toPercent(v: number): string {
  if (!Number.isFinite(v)) return '0%'
  return `${(Math.max(0, Math.min(1, v)) * 100).toFixed(1)}%`
}

/** 根据成功率返回语义化样式名 */
function rateClass(rate: number): 'success' | 'warning' | 'danger' {
  if (rate >= 0.9) return 'success'
  if (rate >= 0.7) return 'warning'
  return 'danger'
}

/** 计算三维评分平均值 */
function avgScore(scores: ThreeDScore[] | undefined, key: keyof ThreeDScore): number {
  if (!scores || scores.length === 0) return 0
  const sum = scores.reduce((acc, s) => acc + (Number(s[key]) || 0), 0)
  return sum / scores.length
}

export default function EvaluationPanel({ evaluation }: EvaluationPanelProps) {
  if (!evaluation) {
    return (
      <div className="report-empty">
        <div className="empty-icon" aria-hidden>i</div>
        <div className="empty-title">暂无评估数据</div>
        <div className="empty-desc">任务完成后将展示工具调用成功率、平均置信度与创新点三维评分。</div>
      </div>
    )
  }

  const {
    tool_call_success_rate: successRate,
    total_tool_calls: totalCalls,
    failed_tool_calls: failedCalls,
    avg_confidence: avgConfidence,
    innovations_scores: scores,
    tool_calls: toolCalls,
  } = evaluation

  const rateCls = rateClass(successRate)
  const avgNovelty = avgScore(scores, 'novelty')
  const avgFeasibility = avgScore(scores, 'feasibility')
  const avgSignificance = avgScore(scores, 'significance')
  // 三维评分满分 10
  const scoreMax = 10

  return (
    <div>
      {/* 顶部指标卡片 */}
      <div className="eval-panel">
        <div className="metric-card">
          <span className="metric-label">工具调用成功率</span>
          <span className={`metric-value ${rateCls}`}>{toPercent(successRate)}</span>
          <div className="metric-bar">
            <div
              className={`metric-bar-fill ${rateCls}`}
              style={{ width: `${Math.max(0, Math.min(1, successRate)) * 100}%` }}
            />
          </div>
        </div>

        <div className="metric-card">
          <span className="metric-label">总工具调用数</span>
          <span className="metric-value">{totalCalls}</span>
          <span className="metric-sub">失败 {failedCalls} 次</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">平均置信度</span>
          <span className={`metric-value ${avgConfidence >= 0.7 ? 'success' : 'warning'}`}>
            {toPercent(avgConfidence)}
          </span>
          <div className="metric-bar">
            <div
              className={`metric-bar-fill ${avgConfidence >= 0.7 ? 'success' : 'warning'}`}
              style={{ width: `${Math.max(0, Math.min(1, avgConfidence)) * 100}%` }}
            />
          </div>
        </div>

        <div className="metric-card">
          <span className="metric-label">创新点数量</span>
          <span className="metric-value">{scores?.length ?? 0}</span>
          <span className="metric-sub">三维评分均值见下</span>
        </div>
      </div>

      {/* 三维评分条形图 */}
      <div className="score-section">
        <h3 className="section-title">创新点三维评分（均值，满分 10）</h3>
        <div className="score-item">
          <div className="score-header">
            <span className="score-name">新颖性 Novelty</span>
            <span className="score-num">{avgNovelty.toFixed(2)} / {scoreMax}</span>
          </div>
          <div className="score-track">
            <div
              className="score-fill novelty"
              style={{ width: `${(avgNovelty / scoreMax) * 100}%` }}
            />
          </div>
        </div>
        <div className="score-item">
          <div className="score-header">
            <span className="score-name">可行性 Feasibility</span>
            <span className="score-num">{avgFeasibility.toFixed(2)} / {scoreMax}</span>
          </div>
          <div className="score-track">
            <div
              className="score-fill feasibility"
              style={{ width: `${(avgFeasibility / scoreMax) * 100}%` }}
            />
          </div>
        </div>
        <div className="score-item">
          <div className="score-header">
            <span className="score-name">显著性 Significance</span>
            <span className="score-num">{avgSignificance.toFixed(2)} / {scoreMax}</span>
          </div>
          <div className="score-track">
            <div
              className="score-fill significance"
              style={{ width: `${(avgSignificance / scoreMax) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* 工具调用明细 */}
      <div className="tool-list">
        <h3 className="section-title">工具调用明细（{toolCalls?.length ?? 0} 条）</h3>
        {toolCalls && toolCalls.length > 0 ? (
          <div>
            <div className="tool-row" style={{ fontWeight: 600, color: 'var(--text-muted)', borderBottom: '2px solid var(--border-strong)' }}>
              <span>工具名</span>
              <span>入参摘要</span>
              <span>状态</span>
              <span style={{ textAlign: 'right' }}>耗时(s)</span>
            </div>
            {toolCalls.map((call, idx) => (
              <div className="tool-row" key={`${call.tool_name}-${idx}`}>
                <span className="tool-name">{call.tool_name}</span>
                <span className="tool-args" title={call.args_summary}>{call.args_summary || '-'}</span>
                <span>
                  <span className={`tool-status ${call.success ? 'ok' : 'fail'}`}>
                    {call.success ? '成功' : '失败'}
                  </span>
                </span>
                <span className="tool-duration">{call.duration_sec?.toFixed(2) ?? '-'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
            暂无工具调用记录
          </div>
        )}
      </div>
    </div>
  )
}
