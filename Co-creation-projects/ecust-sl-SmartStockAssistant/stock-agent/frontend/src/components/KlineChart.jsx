import { Card, Empty } from 'antd'
import {
  ResponsiveContainer, ComposedChart, Bar, Line,
  XAxis, YAxis, Tooltip, Legend,
} from 'recharts'

export default function KlineChart({ klineData }) {
  if (!klineData || klineData.length === 0) {
    return (
      <Card title="K 线走势" size="small" style={{ height: '100%' }}>
        <Empty description="暂无 K 线数据" />
      </Card>
    )
  }

  const data = klineData.slice(-20).map(bar => ({
    date: bar.date?.slice(5),   // 只显示 MM-DD
    open: bar.open,
    close: bar.close,
    high: bar.high,
    low: bar.low,
    volume: Math.round(bar.volume / 10000),  // 转换为万手
    isUp: bar.close >= bar.open,
  }))

  return (
    <Card title="K 线走势（近 20 日）" size="small" style={{ height: '100%' }}>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis
            yAxisId="price"
            domain={['auto', 'auto']}
            tick={{ fontSize: 11 }}
            width={60}
          />
          <YAxis
            yAxisId="volume"
            orientation="right"
            tick={{ fontSize: 11 }}
            width={40}
          />
          <Tooltip
            formatter={(val, name) => {
              if (name === '成交量') return [`${val} 万手`, name]
              return [val?.toFixed(2), name]
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            yAxisId="volume"
            dataKey="volume"
            name="成交量"
            fill="#B4B2A9"
            opacity={0.5}
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="close"
            name="收盘价"
            stroke="#185FA5"
            dot={false}
            strokeWidth={2}
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="high"
            name="最高价"
            stroke="#1D9E75"
            dot={false}
            strokeWidth={1}
            strokeDasharray="3 3"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  )
}