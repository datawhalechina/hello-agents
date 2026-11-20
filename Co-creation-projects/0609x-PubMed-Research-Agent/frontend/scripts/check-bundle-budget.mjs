import { gzipSync } from 'node:zlib'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const distDirectory = resolve(scriptDirectory, '..', 'dist')
const assetsDirectory = join(distDirectory, 'assets')
const indexHtml = readFileSync(join(distDirectory, 'index.html'), 'utf8')

const limits = {
  initialJavaScriptGzipKiB: 200,
  initialCssGzipKiB: 40,
  largestJavaScriptKiB: 450
}

const initialAssetPaths = [
  ...indexHtml.matchAll(/(?:src|href)="([^"]+\.(?:js|css))"/g)
].map((match) => match[1])

const gzipKiB = (path) => gzipSync(readFileSync(path)).byteLength / 1024
const resolveAsset = (assetPath) => join(distDirectory, assetPath.replace(/^\//, ''))

const initialJavaScript = [...new Set(initialAssetPaths.filter((path) => path.endsWith('.js')))]
const initialCss = [...new Set(initialAssetPaths.filter((path) => path.endsWith('.css')))]
const initialJavaScriptGzipKiB = initialJavaScript.reduce(
  (total, path) => total + gzipKiB(resolveAsset(path)),
  0
)
const initialCssGzipKiB = initialCss.reduce(
  (total, path) => total + gzipKiB(resolveAsset(path)),
  0
)

const javaScriptAssets = readdirSync(assetsDirectory)
  .filter((name) => name.endsWith('.js'))
  .map((name) => ({ name, sizeKiB: statSync(join(assetsDirectory, name)).size / 1024 }))
const largestJavaScript = javaScriptAssets.sort((a, b) => b.sizeKiB - a.sizeKiB)[0]

const checks = [
  {
    name: '首屏 JavaScript (gzip)',
    actual: initialJavaScriptGzipKiB,
    limit: limits.initialJavaScriptGzipKiB
  },
  {
    name: '首屏 CSS (gzip)',
    actual: initialCssGzipKiB,
    limit: limits.initialCssGzipKiB
  },
  {
    name: `最大 JavaScript 分块 (${largestJavaScript.name})`,
    actual: largestJavaScript.sizeKiB,
    limit: limits.largestJavaScriptKiB
  }
]

let failed = false
for (const check of checks) {
  const passed = check.actual <= check.limit
  failed ||= !passed
  console.log(
    `${passed ? 'PASS' : 'FAIL'} ${check.name}: ${check.actual.toFixed(1)} KiB / ${check.limit} KiB`
  )
}

if (failed) {
  console.error('前端包体积超过预算，请检查新增依赖或拆分边界。')
  process.exitCode = 1
}
