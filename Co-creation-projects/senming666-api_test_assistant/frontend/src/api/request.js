import axios from 'axios'

/**
 * 创建 axios 实例 —— 整个项目所有请求共用的"模板"
 * 好处：超时时间、请求头、错误处理逻辑只写一遍
 */
const request = axios.create({
  // baseURL 留空 → 请求走相对路径（/api/...）
  // 开发环境由 Vite 代理转发到后端；生产环境前后端同源，天然可用
  baseURL: '',
  // 测试流程要走 LLM 生成用例，可能较久，超时给足 600 秒
  timeout: 600000,
})

// 请求拦截器：发请求之前做统一处理（这里暂不需要，保留结构）
request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
)

// 响应拦截器：拿到响应之后做统一处理
request.interceptors.response.use(
  // 成功回调：后端返回的数据结构是 { summary, results }，
  // 我们只关心 body，所以直接剥掉 axios 外壳，返回 response.data
  (response) => response.data,

  // 失败回调：把各种错误统一成一个带 message 的 Error，方便组件里用
  (error) => {
    // FastAPI 出错时返回 {"detail": "错误信息"}，放在 error.response.data.detail
    const detail = error.response?.data?.detail
    const message = detail || error.message || '网络请求失败'
    return Promise.reject(new Error(message))
  },
)

export default request
