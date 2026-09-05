import { useEffect, useState } from 'react'
import { Steps, Card, Typography } from 'antd'

const { Text } = Typography

// 根据 elapsed 估计当前阶段。后端实测 60s 左右，按比例推进。
const STAGES = [
  { title: '采集数据', desc: '获取行情 / K 线 / 新闻', endRatio: 0.15 },
  { title: '三维分析', desc: '情感 + 技术 + 基本面并行', endRatio: 0.45 },
  { title: '生成报告', desc: 'AI 综合解读中', endRatio: 0.95 },
  { title: '完成', desc: '渲染结果', endRatio: 1.0 },
]

const ESTIMATED_TOTAL_MS = 60_000

export default function AnalysisProgress({ active }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!active) {
      setElapsed(0)
      return
    }
    const start = Date.now()
    const timer = setInterval(() => {
      setElapsed(Date.now() - start)
    }, 500)
    return () => clearInterval(timer)
  }, [active])

  if (!active) return null

  const ratio = Math.min(elapsed / ESTIMATED_TOTAL_MS, 0.95)
  let current = 0
  for (let i = 0; i < STAGES.length; i++) {
    if (ratio < STAGES[i].endRatio) {
      current = i
      break
    }
    current = i
  }

  const seconds = Math.floor(elapsed / 1000)

  return (
    <Card size="small" styles={{ body: { padding: '20px 24px' } }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <Text strong>分析进度</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>已用 {seconds}s · 预计 ~60s</Text>
      </div>
      <Steps
        current={current}
        size="small"
        items={STAGES.map((s) => ({ title: s.title, content: s.desc }))}
      />
    </Card>
  )
}
