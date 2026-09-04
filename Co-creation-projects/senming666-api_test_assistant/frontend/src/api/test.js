import request from './request'

/**
 * 调用后端一键测试接口
 * @param {Object} payload - { openapi_text, base_url } 或 { openapi_url, base_url }
 * @returns {Promise<{summary: Object, results: Array}>}
 */
export function runApiTest(payload) {
  // 因为拦截器已经剥壳，这里 resolve 出来的直接就是后端返回的 JSON body
  return request.post('/api/test', payload)
}
