import { useEffect, useId, useState } from 'react'
import { LoaderCircle, Minus, Plus, RotateCcw } from 'lucide-react'

export function mermaidBlocks(markdown: string) {
  const blocks: string[] = []
  let fence = '', length = 0, capture = false, content: string[] = []
  for (const line of markdown.split(/\r?\n/)) {
    if (!fence) {
      const open = /^ {0,3}(`{3,}|~{3,})([^\r\n]*)$/.exec(line)
      if (open) { fence = open[1][0]; length = open[1].length; capture = open[2].trim().split(/\s/)[0].toLowerCase() === 'mermaid'; content = [] }
    } else {
      const close = /^ {0,3}([`~]+)[ \t]*$/.exec(line)
      if (close && close[1][0] === fence && [...close[1]].every(char => char === fence) && close[1].length >= length) {
        if (capture) blocks.push(content.join('\n'))
        fence = ''; capture = false
      } else if (capture) content.push(line)
    }
  }
  return blocks
}

function decodedSource(source: string) {
  let value = source
  for (let i = 0; i < 8; i += 1) {
    const next = value.replace(/&#(x[0-9a-f]+|\d+);?|&(amp|lt|gt|quot|apos|colon|sol);/gi, (match, code: string | undefined, name: string | undefined) => {
      if (code) { const point = parseInt(code[0].toLowerCase() === 'x' ? code.slice(1) : code, code[0].toLowerCase() === 'x' ? 16 : 10); return point > 0 && point <= 0x10ffff ? String.fromCodePoint(point) : '\ufffd' }
      return ({ amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", colon: ':', sol: '/' } as Record<string, string>)[name?.toLowerCase() || ''] || match
    })
    if (next === value) break
    value = next
  }
  return value
}

function validateSource(source: string) {
  if (source.length > 50000) throw new Error('图示超过本地预览规模限制，请查看源码。')
  // Mermaid draws attribute-free break tags as SVG text line breaks.
  // Keep the original source for rendering and inspect all other markup.
  const value = decodedSource(source).replace(/<br\s*\/?>/gi, '')
  if (!/^\s*(?:flowchart|graph)(?:[ \t]+(?:TB|TD|BT|LR|RL))?[ \t]*(?:\r?\n|;|$)/i.test(value)) throw new Error('当前安全预览仅支持 Mermaid flowchart / graph，请查看源码。')
  if (/%%\s*(?:\{|init\b|config\b)|^\s*---|\b(?:themeCSS|securityLevel|htmlLabels|classDef|linkStyle)\b|(?:^|[;\n])\s*(?:click|style|class)\b|\bclick\s+|<\s*[!/a-z]|\b(?:https?|ftp|file|javascript|vbscript|data|mailto)\s*:|\/\/|@\s*\{|\$\$/im.test(value)) throw new Error('图示包含不支持的链接、HTML、交互或配置指令，已保留源码。')
}

function unsafeCss(value: string) {
  if (/@import|expression\s*\(|javascript:|https?:|data:|\\/i.test(value)) return true
  return [...value.matchAll(/url\s*\(([^)]*)\)/gi)].some(match => !match[1].trim().replace(/^['"]|['"]$/g, '').startsWith('#'))
}

async function sanitizedDocument(svg: string) {
  const { default: purifier } = await import('dompurify')
  const clean = purifier.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true }, FORBID_TAGS: ['script', 'foreignObject', 'image', 'a', 'iframe', 'object', 'embed', 'animate', 'animateTransform', 'set'], FORBID_ATTR: ['href', 'xlink:href', 'src'] })
  const doc = new DOMParser().parseFromString(clean, 'image/svg+xml')
  if (doc.querySelector('parsererror') || doc.documentElement.localName !== 'svg') throw new Error('本地无法读取此图示，请查看源码。')
  const allowed = new Set(['svg', 'g', 'defs', 'marker', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line', 'text', 'tspan', 'title', 'desc', 'style', 'clippath', 'lineargradient', 'stop'])
  for (const element of [...doc.querySelectorAll('*')]) {
    if (!allowed.has(element.localName.toLowerCase())) { element.remove(); continue }
    if (element.localName === 'style' && unsafeCss(element.textContent || '')) { element.remove(); continue }
    for (const attribute of [...element.attributes]) {
      if (/^on|href$|^src$/i.test(attribute.name) || unsafeCss(attribute.value)) element.removeAttribute(attribute.name)
    }
  }
  const root = doc.documentElement
  const box = (root.getAttribute('viewBox') || '').trim().split(/[ ,]+/).map(Number)
  const width = box[2], height = box[3]
  if (box.length !== 4 || !box.every(Number.isFinite) || width <= 0 || height <= 0 || width > 20000 || height > 20000) throw new Error('图示尺寸不适合本地预览，请查看源码。')
  root.setAttribute('width', '100%'); root.setAttribute('height', '100%')
  const xml = new XMLSerializer().serializeToString(root)
  const csp = "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
  return { width, height, document: `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${csp}"><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#fff}svg{display:block}</style></head><body>${xml}</body></html>` }
}

let rendering: Promise<unknown> = Promise.resolve()
function render(source: string, id: string) {
  const result = rendering.catch(() => undefined).then(async () => {
    validateSource(source)
    const { default: mermaid } = await import('mermaid')
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', htmlLabels: false, suppressErrorRendering: true, maxTextSize: 50000, maxEdges: 500, theme: 'base', fontFamily: 'Segoe UI, Microsoft YaHei, sans-serif', themeVariables: { primaryColor: '#edf3fd', primaryTextColor: '#182b49', primaryBorderColor: '#8ea9d1', lineColor: '#6583ad', secondaryColor: '#f3f7fb', tertiaryColor: '#f8fafc' }, flowchart: { useMaxWidth: false }, secure: ['secure', 'securityLevel', 'htmlLabels', 'startOnLoad', 'maxTextSize', 'maxEdges', 'suppressErrorRendering', 'themeCSS'] })
    const { svg } = await mermaid.render(id, source)
    // No bindFunctions: model-authored nodes never receive click handlers.
    return sanitizedDocument(svg)
  })
  rendering = result
  return result
}

export default function MermaidDiagram({ source, pending = false }: { source: string; pending?: boolean }) {
  const id = `model-mermaid-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  const [value, setValue] = useState<{ width: number; height: number; document: string } | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [zoom, setZoom] = useState(1)
  useEffect(() => {
    let active = true
    setValue(null); setError(''); setZoom(1); setLoading(!pending)
    if (!pending) render(source, id).then(result => { if (active) setValue(result) }).catch(failure => { if (active) setError(failure instanceof Error && /源码/.test(failure.message) ? failure.message : '图示格式暂时无法绘制，请查看源码；不会自动重新调用模型。') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [source, id, pending])
  return <section className="mermaid-diagram" aria-label="模型项目图示，非核验事实"><div className="mermaid-diagram-heading"><span>模型图示 · 非核验事实</span>{value && <div><button className="icon-button" aria-label="缩小图示" disabled={zoom <= 0.2} onClick={() => setZoom(current => Math.max(0.2, current - 0.2))}><Minus size={14} /></button><span>{Math.round(zoom * 100)}%</span><button className="icon-button" aria-label="放大图示" disabled={zoom >= 3} onClick={() => setZoom(current => Math.min(3, current + 0.2))}><Plus size={14} /></button><button className="icon-button" aria-label="重置图示缩放" onClick={() => setZoom(1)}><RotateCcw size={14} /></button></div>}</div>{loading && <p className="mermaid-render-status" role="status"><LoaderCircle size={15} className="spin" />正在本地绘图，不调用模型…</p>}{pending && <p className="mermaid-render-status">图示源码仍在生成，结束后在本地绘制。</p>}{error && <p className="mermaid-render-error" role="status">{error}</p>}{value && <div className="mermaid-viewport" tabIndex={0} role="region" aria-label="模型图示，可横向和纵向滚动" style={{ maxHeight: 620 }}><iframe title="隔离的模型流程图" sandbox="" referrerPolicy="no-referrer" srcDoc={value.document} style={{ width: Math.max(240, value.width * zoom), height: Math.max(140, value.height * zoom) }} /></div>}<details className="mermaid-source" open={!!error || pending}><summary>查看 Mermaid 源码</summary><pre>{source}</pre></details></section>
}
