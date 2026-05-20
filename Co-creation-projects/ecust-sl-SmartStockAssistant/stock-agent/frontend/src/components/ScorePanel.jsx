import { Card, Progress, Tag, Divider } from 'antd'
import {
  SmileOutlined, FundOutlined, BankOutlined,
} from '@ant-design/icons'

const SENTIMENT_LABEL = {
  positive: { color: 'success', text: '乐观' },
  neutral:  { color: 'default', text: '中性' },
  negative: { color: 'error',   text: '悲观' },
}

export default function ScorePanel({ scores }) {
  if (!scores) return null

  const {
    sentiment, sentiment_label, sentiment_reason,
    technical, technical_signals,
    fundamental, fundamental_signals,
  } = scores

  const sentimentPct = sentiment != null
    ? Math.round((sentiment + 1) / 2 * 100)
    : 50

  const items = [
    {
      icon: <SmileOutlined />,
      label: '情感评分',
      score: sentimentPct,
      color: '#7F77DD',
      extra: sentiment_label
        ? <Tag color={SENTIMENT_LABEL[sentiment_label]?.color}>
            {SENTIMENT_LABEL[sentiment_label]?.text}
          </Tag>
        : null,
      detail: sentiment_reason,
      signals: [],
    },
    {
      icon: <FundOutlined />,
      label: '技术面评分',
      score: Math.round(technical ?? 50),
      color: '#185FA5',
      signals: technical_signals?.slice(0, 3) || [],
    },
    {
      icon: <BankOutlined />,
      label: '基本面评分',
      score: Math.round(fundamental ?? 50),
      color: '#1D9E75',
      signals: fundamental_signals?.slice(0, 3) || [],
    },
  ]

  return (
    <Card title="三维评分" size="small" style={{ height: '100%' }}>
      {items.map((item, i) => (
        <div key={i}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 13, color: '#555' }}>
              {item.icon} {item.label}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {item.extra}
              <span style={{ fontWeight: 500 }}>{item.score}</span>
            </div>
          </div>
          <Progress
            percent={item.score}
            strokeColor={item.color}
            showInfo={false}
            size="small"
          />
          {item.detail && (
            <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
              {item.detail}
            </div>
          )}
          {item.signals.length > 0 && (
            <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {item.signals.map((s, j) => (
                <Tag key={j} style={{ fontSize: 11, margin: 0 }}>{s}</Tag>
              ))}
            </div>
          )}
          {i < items.length - 1 && <Divider style={{ margin: '10px 0' }} />}
        </div>
      ))}
    </Card>
  )
}