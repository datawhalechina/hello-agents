import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Badge } from 'antd'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { fetchHotStocks } from '../api/client'

const { Title, Text } = Typography

// 三市强区分色系：A股 蓝、港股 红、美股 绿
const MARKET_META = {
  'A股':  {
    accent: '#1B66B2',
    cardBg: 'linear-gradient(180deg, #F0F7FF 0%, #FFFFFF 60%)',
    headerBg: '#1B66B2',
    headerFg: '#FFFFFF',
    badge: 'A 股',
  },
  '港股': {
    accent: '#C0392B',
    cardBg: 'linear-gradient(180deg, #FFF1EE 0%, #FFFFFF 60%)',
    headerBg: '#C0392B',
    headerFg: '#FFFFFF',
    badge: '港 股',
  },
  '美股': {
    accent: '#2E7D32',
    cardBg: 'linear-gradient(180deg, #F1F9EE 0%, #FFFFFF 60%)',
    headerBg: '#2E7D32',
    headerFg: '#FFFFFF',
    badge: '美 股',
  },
}

// 中国市场约定：红涨 / 绿跌
const colorOf = (pct) => {
  if (pct == null) return '#999'
  if (pct > 0) return '#C0392B'
  if (pct < 0) return '#1E8449'
  return '#666'
}

function Sparkline({ data, positive }) {
  if (!data || data.length < 2) {
    return <div style={{ height: 28 }} />
  }
  const series = data.map((v, i) => ({ i, v }))
  return (
    <div style={{ height: 28, width: '100%', minWidth: 80 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={positive ? '#C0392B' : '#1E8449'}
            strokeWidth={1.6}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function StockCard({ stock, rank, accent, onClick }) {
  const pct = stock.change_pct
  const positive = (pct ?? 0) >= 0
  const priceColor = colorOf(pct)
  const noData = stock.price == null

  return (
    <div
      onClick={() => !noData && onClick(stock)}
      style={{
        padding: '10px 12px 8px 10px',
        borderRadius: 6,
        background: 'var(--ant-color-fill-quaternary, #fafafa)',
        cursor: noData ? 'not-allowed' : 'pointer',
        opacity: noData ? 0.55 : 1,
        marginBottom: 8,
        border: '1px solid rgba(0,0,0,0.04)',
        borderLeft: `3px solid ${accent}`,
        transition: 'transform .15s, box-shadow .15s',
      }}
      onMouseEnter={(e) => {
        if (noData) return
        e.currentTarget.style.transform = 'translateY(-1px)'
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = ''
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ minWidth: 0, flex: 1, display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span style={{
            fontSize: 11,
            color: '#fff',
            background: accent,
            borderRadius: 3,
            padding: '0 5px',
            fontWeight: 600,
            minWidth: 18,
            textAlign: 'center',
          }}>{rank}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, lineHeight: 1.2 }}>{stock.name}</div>
            <Text type="secondary" style={{ fontSize: 11 }}>{stock.symbol}</Text>
          </div>
        </div>
        <div style={{ textAlign: 'right', marginLeft: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: priceColor, lineHeight: 1.2 }}>
            {noData ? '—' : stock.price}
          </div>
          <div style={{ fontSize: 11, color: priceColor, fontWeight: 600 }}>
            {noData ? '无数据' : `${pct > 0 ? '+' : ''}${pct}%`}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 4 }}>
        <Sparkline data={stock.sparkline} positive={positive} />
      </div>
    </div>
  )
}

export default function HotStocks({ onPick }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetchHotStocks()
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(e.message || '热门股票加载失败') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <Spin tip="正在加载今日涨幅榜…" />
      </div>
    )
  }

  if (error || !data) {
    return <Empty description={error || '暂无数据'} />
  }

  const markets = ['A股', '港股', '美股']

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Title level={4} style={{ margin: 0 }}>📈 今日涨幅榜 · Top 8</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>三市当日涨幅前 8 · 点击卡片直接分析 · 缓存 5 分钟</Text>
      </div>
      <Row gutter={16}>
        {markets.map((mkt) => {
          const meta = MARKET_META[mkt]
          const stocks = data[mkt] || []
          return (
            <Col key={mkt} xs={24} md={8}>
              <Card
                size="small"
                style={{
                  background: meta.cardBg,
                  borderTop: `3px solid ${meta.accent}`,
                }}
                title={
                  <span style={{
                    color: meta.headerFg,
                    background: meta.headerBg,
                    margin: '-12px -16px -12px -16px',
                    padding: '8px 16px',
                    display: 'block',
                    fontWeight: 600,
                    letterSpacing: 1,
                  }}>
                    {meta.badge}
                    <Badge
                      count={stocks.length}
                      style={{
                        backgroundColor: 'rgba(255,255,255,0.25)',
                        color: '#fff',
                        marginLeft: 10,
                        fontWeight: 500,
                      }}
                    />
                  </span>
                }
                styles={{
                  header: { padding: 0, border: 'none' },
                  body: { padding: 12 },
                }}
              >
                {stocks.map((s, idx) => (
                  <StockCard
                    key={`${mkt}-${s.symbol}`}
                    stock={s}
                    rank={idx + 1}
                    accent={meta.accent}
                    onClick={onPick}
                  />
                ))}
                {stocks.length === 0 && (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
                )}
              </Card>
            </Col>
          )
        })}
      </Row>
    </div>
  )
}
