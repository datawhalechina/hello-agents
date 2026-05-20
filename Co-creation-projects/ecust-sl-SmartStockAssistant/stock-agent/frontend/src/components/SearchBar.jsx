import { useState, useCallback } from 'react'
import { AutoComplete, Select, Button, Space, message } from 'antd'
import { SearchOutlined, StockOutlined } from '@ant-design/icons'
import { searchStock } from '../api/client'

const { Option } = Select

export default function SearchBar({ onAnalyze, loading }) {
  const [options, setOptions]   = useState([])
  const [selected, setSelected] = useState(null)  // { symbol, name, market }
  const [market, setMarket]     = useState('A股')
  const [inputVal, setInputVal] = useState('')

  const handleSearch = useCallback(async (val) => {
    setInputVal(val)
    if (!val || val.length < 1) {
      setOptions([])
      return
    }
    try {
      const results = await searchStock(val)
      setOptions(results.map(s => {
        const palette = {
          'A股':  { bg: '#E6F1FB', fg: '#185FA5' },
          '港股': { bg: '#FDECEC', fg: '#A8201A' },
          '美股': { bg: '#EAF3DE', fg: '#3B6D11' },
        }[s.market] || { bg: '#EEE', fg: '#666' }
        return {
          value: s.symbol,
          label: (
            <Space>
              <span style={{ fontWeight: 500 }}>{s.symbol}</span>
              <span style={{ color: '#888', fontSize: 12 }}>{s.name}</span>
              <span style={{
                fontSize: 11, padding: '1px 6px',
                background: palette.bg,
                color: palette.fg,
                borderRadius: 4,
              }}>
                {s.market}
              </span>
            </Space>
          ),
          market: s.market,
          name: s.name,
        }
      }))
    } catch {
      setOptions([])
    }
  }, [])

  const handleSelect = (val, option) => {
    setSelected({ symbol: val, name: option.name, market: option.market })
    setMarket(option.market)
    setInputVal(`${val} ${option.name}`)
  }

  const handleAnalyze = () => {
    const symbol = selected?.symbol || inputVal.trim().split(' ')[0]
    if (!symbol) {
      message.warning('请输入股票代码或名称')
      return
    }
    onAnalyze(symbol, market)
  }

  return (
    <Space.Compact style={{ width: '100%' }}>
      <AutoComplete
        style={{ flex: 1 }}
        options={options}
        onSearch={handleSearch}
        onSelect={handleSelect}
        value={inputVal}
        onChange={setInputVal}
        placeholder="输入代码或名称，如 茅台 / 600519 / 00700 / AAPL"
        size="large"
        allowClear
        onClear={() => { setSelected(null); setOptions([]) }}
      >
      </AutoComplete>

      <Select
        value={market}
        onChange={setMarket}
        size="large"
        style={{ width: 100 }}
      >
        <Option value="A股">A 股</Option>
        <Option value="港股">港 股</Option>
        <Option value="美股">美 股</Option>
      </Select>

      <Button
        type="primary"
        size="large"
        icon={<SearchOutlined />}
        loading={loading}
        onClick={handleAnalyze}
      >
        {loading ? "分析中（约20秒）" : "分析"}
      </Button>
    </Space.Compact>
  )
}