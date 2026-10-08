/**
 * RSA 加密工具模块
 * 使用浏览器 Web Crypto API 进行 RSA-OAEP 加密
 */

let _publicKeyCache: CryptoKey | null = null
let _publicKeyPemCache: string | null = null

/**
 * 从后端获取 RSA 公钥（PEM 格式，带缓存）
 */
export async function fetchPublicKey(): Promise<string> {
  if (_publicKeyPemCache) return _publicKeyPemCache

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://localhost:8000'
  const res = await fetch(`${baseUrl}/api/auth/public-key`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error('获取公钥失败')
  const data = await res.json()
  if (!data.success || !data.public_key) throw new Error('公钥数据异常')

  _publicKeyPemCache = data.public_key
  return data.public_key
}

/**
 * 将 PEM 格式公钥导入为 Web Crypto API 的 CryptoKey
 */
function pemToCryptoKey(pem: string): Promise<CryptoKey> {
  // 移除 PEM 头尾和换行
  const pemHeader = '-----BEGIN PUBLIC KEY-----'
  const pemFooter = '-----END PUBLIC KEY-----'
  const pemContents = pem.substring(pemHeader.length, pem.indexOf(pemFooter))
  const binaryDer = Uint8Array.from(atob(pemContents.replace(/\s/g, '')), c => c.charCodeAt(0))

  return crypto.subtle.importKey(
    'spki',
    binaryDer.buffer,
    {
      name: 'RSA-OAEP',
      hash: { name: 'SHA-256' },
    },
    false,
    ['encrypt'],
  )
}

/**
 * 使用 RSA 公钥加密明文密码
 * @param password 明文密码
 * @param publicKeyPem PEM 格式的公钥（若不传则自动从后端获取）
 * @returns Base64 编码的密文
 */
export async function rsaEncrypt(password: string, publicKeyPem?: string): Promise<string> {
  if (!publicKeyPem) {
    publicKeyPem = await fetchPublicKey()
  }

  // 缓存 CryptoKey 避免重复导入
  if (!_publicKeyCache) {
    _publicKeyCache = await pemToCryptoKey(publicKeyPem)
  }

  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    _publicKeyCache,
    new TextEncoder().encode(password),
  )

  // ArrayBuffer → Base64
  const bytes = new Uint8Array(encrypted)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

/**
 * 清除缓存的公钥（用于测试或重新获取）
 */
export function clearPublicKeyCache() {
  _publicKeyCache = null
  _publicKeyPemCache = null
}
