/**
 * 通用的「安全显示」工具。
 * 后端字段有时是 null / undefined / 空串，直接渲染成空白很丑，
 * 统一在这里转成占位符或字符串。
 */

/**
 * 简单展示：null/undefined/空串 → fallback，对象 → JSON 字符串
 */
export function display(value, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/**
 * 格式化 JSON 用于「多行查看」：对象或合法 JSON 字符串 → 缩进后的文本；
 * 非 JSON 的普通字符串原样返回，方便在 <pre> 里展示
 */
export function prettyJson(value) {
  if (value === null || value === undefined || value === '') return '(空)'
  if (typeof value === 'string') {
    try {
      // 字符串里可能存的是 JSON 文本，尝试二次解析再美化
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value // 解析失败说明就是普通文本，原样返回
    }
  }
  // 已经是对象/数组，直接美化
  return JSON.stringify(value, null, 2)
}
