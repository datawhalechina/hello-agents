import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 180000,
})

// 搜索股票（代码或名称）
export const searchStock = (q) =>
  client.get('/api/v1/search', { params: { q } }).then(r => r.data)

// 执行分析
export const analyzeStock = (symbol, market) =>
  client.post('/api/v1/analyze', { symbol, market }).then(r => r.data)

// 三市热门股票
export const fetchHotStocks = () =>
  client.get('/api/v1/hot/all').then(r => r.data)

// 健康检查
export const healthCheck = () =>
  client.get('/health').then(r => r.data)