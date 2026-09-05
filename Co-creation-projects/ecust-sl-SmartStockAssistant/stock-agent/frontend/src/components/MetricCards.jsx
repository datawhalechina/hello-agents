import { Row, Col, Statistic, Tag, Card } from 'antd'
import { RiseOutlined, FallOutlined, SafetyCertificateOutlined } from '@ant-design/icons'

const RISK_MAP = {
  low:    { color: 'success', label: '低风险' },
  medium: { color: 'warning', label: '中等风险' },
  high:   { color: 'error',   label: '高风险' },
}

export default function MetricCards({ result }) {
  if (!result) return null

  const { symbol, market, risk_level, scores, realtime_data } = result

  const price     = realtime_data?.price ?? '--'
  const changePct = realtime_data?.change_pct ?? 0
  const isUp      = changePct >= 0
  const risk      = RISK_MAP[risk_level] || RISK_MAP.medium

  // 三维加权平均：情感转换到0-100区间
  const sentimentPct = scores?.sentiment != null
    ? ((scores.sentiment + 1) / 2 * 100)
    : 50
  const avgScore = (
    sentimentPct * 0.33 +
    (scores?.technical ?? 50) * 0.33 +
    (scores?.fundamental ?? 50) * 0.34
  ).toFixed(1)

  return (
    <Row gutter={12}>
      {[
        {
          title: `${symbol} · ${market}`,
          value: typeof price === 'number' ? price.toFixed(2) : '--',
          suffix: '元',
        },
        {
          title: '涨跌幅',
          value: Math.abs(changePct).toFixed(2),
          prefix: isUp
            ? <RiseOutlined style={{ color: '#3B6D11' }} />
            : <FallOutlined style={{ color: '#A32D2D' }} />,
          suffix: '%',
          valueStyle: { color: isUp ? '#3B6D11' : '#A32D2D' },
        },
        {
          title: '综合评分',
          value: avgScore,
          suffix: '/ 100',
        },
        {
          title: '风险等级',
          value: null,
          custom: (
            <Tag
              color={risk.color}
              icon={<SafetyCertificateOutlined />}
              style={{ fontSize: 14, padding: '4px 12px', marginTop: 4 }}
            >
              {risk.label}
            </Tag>
          ),
        },
      ].map((item, i) => (
        <Col span={6} key={i}>
          <Card size="small" styles={{ body: { padding: '12px 16px' } }}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>
              {item.title}
            </div>
            {item.custom || (
              <Statistic
                value={item.value}
                prefix={item.prefix}
                suffix={item.suffix}
                valueStyle={item.valueStyle}
              />
            )}
          </Card>
        </Col>
      ))}
    </Row>
  )
}