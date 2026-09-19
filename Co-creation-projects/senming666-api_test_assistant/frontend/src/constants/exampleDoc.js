// 示例 OpenAPI 文档：和仓库根目录 api.yaml 内容一致（JSONPlaceholder 两个 GET 接口）
export const EXAMPLE_DOC = `openapi: 3.0.0
info:
  title: JSONPlaceholder 测试API
  description: 用于测试智能API测试助手的示例文档
  version: 1.0.0
paths:
  /users:
    get:
      summary: 获取用户列表
      responses:
        '200':
          description: 成功返回用户列表
  /posts:
    get:
      summary: 获取帖子列表
      responses:
        '200':
          description: 成功返回帖子列表
`

// 配套的示例被测地址
export const EXAMPLE_BASE_URL = 'https://jsonplaceholder.typicode.com'

// 用例类型 → 中文名（后端返回英文 case_type）
export const CASE_TYPE_LABELS = {
  normal: '正常',
  boundary: '边界',
  error: '异常',
}

// 用例类型 → Element Plus tag 的颜色
export const CASE_TYPE_TAGS = {
  normal: 'success',
  boundary: 'warning',
  error: 'danger',
}

// HTTP 方法 → 标签颜色（模拟常见 API 文档配色：GET绿/POST蓝/PUT橙/DELETE红）
export const METHOD_TAGS = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  DELETE: 'danger',
  PATCH: 'info',
}

// 兜底显示
export const FALLBACK_LABEL = '-'
