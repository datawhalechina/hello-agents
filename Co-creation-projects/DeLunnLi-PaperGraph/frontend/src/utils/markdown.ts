import katex from 'katex'
import 'katex/dist/katex.min.css'
export function clipTextAvoidBreakingMath(s: string, max: number): string {
  if (!s || s.length <= max) return s
  let cut = max
  const before = s.slice(0, max)
  const lastDollar = before.lastIndexOf('$')
  if (lastDollar >= 0) {
    const after = before.slice(lastDollar)
    if (after.indexOf('$', 1) === -1) cut = lastDollar
  }
  return `${s.slice(0, Math.max(0, cut)).trimEnd()}…`
}
function escapeHtmlForMathFallback(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}
function normalizeLatexDelimiters(text: string): string {
  return String(text)
    .replace(/([A-Za-z0-9])\\textsuperscript\{([^}]+)\}/g, '$1$^{$2}$')
    .replace(/\\textsuperscript\{([^}]+)\}/g, '$^{$1}$')
}
export function renderMarkdownWithLatex(text: string): string {
  if (!text) return ''
  const raw = normalizeLatexDelimiters(text)
  const katexHtml: string[] = []
  const withPlaceholders = raw.replace(/\$([^$]+)\$/g, (_, tex) => {
    const t = String(tex).trim()
    let h: string
    try { h = katex.renderToString(t, { displayMode: false, throwOnError: false, output: 'html', strict: 'ignore' }) }
    catch { h = `<span class="latex-inline__txt">${escapeHtmlForMathFallback(`$${t}$`)}</span>` }
    const idx = katexHtml.length; katexHtml.push(h)
    return `[[[LATEXPH${idx}]]]`
  })
  let html = renderMarkdown(withPlaceholders)
  for (let i = 0; i < katexHtml.length; i++) { html = html.split(`[[[LATEXPH${i}]]]`).join(katexHtml[i]) }
  return html
}
export function repairTabSeparatedPseudoTables(text: string): string {
  const raw = String(text || '').replace(/\r\n/g, '\n')
  const lines = raw.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const tabCount = (line.match(/\t/g) || []).length
    if (tabCount === 1 && line.trim() && !line.trimStart().startsWith('|')) {
      const block: string[] = []
      let j = i
      while (j < lines.length) {
        const L = lines[j]
        if (!L.trim()) break
        if (L.trimStart().startsWith('|')) break
        if ((L.match(/\t/g) || []).length !== 1) break
        block.push(L)
        j++
      }
      if (block.length >= 2) {
        const rows = block.map((ln) => {
          const [a, b] = ln.split('\t')
          return [String(a ?? '').trim(), String(b ?? '').trim()]
        })
        if (rows.every((r) => r.length === 2 && r[0] && r[1])) {
          const header = '| ' + rows[0][0] + ' | ' + rows[0][1] + ' |'
          const sep = '| --- | --- |'
          const body = rows
            .slice(1)
            .map((r) => '| ' + r[0] + ' | ' + r[1] + ' |')
            .join('\n')
          out.push(header, sep, body)
          i = j
          if (i < lines.length && !lines[i].trim()) {
            out.push('')
            i++
          }
          continue
        }
      }
    }
    out.push(line)
    i++
  }
  return out.join('\n')
}
export function renderMarkdown(text: string): string {
  if (!text) return ''
  const repaired = repairTabSeparatedPseudoTables(String(text))
  const normalized = repaired.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
  let html = normalized
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/(^|\n)---(?=\n|$)/g, '$1<hr>')
    .replace(/^###### (.*$)/gim, '<h6>$1</h6>').replace(/^##### (.*$)/gim, '<h5>$1</h5>').replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>').replace(/^## (.*$)/gim, '<h2>$1</h2>').replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^\* (.*$)/gim, '<li>$1</li>').replace(/^- (.*$)/gim, '<li>$1</li>')
    .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    const hasNumbers = /^\d+\. /.test(text.substring(text.indexOf(match) - 10, text.indexOf(match)))
    return hasNumbers ? `<ol>${match}</ol>` : `<ul>${match}</ul>`
  })
  html = html.replace(/((?:^\|.+\|\n?)+)/gm, (tableBlock) => {
    const rows = tableBlock.trim().split('\n').filter(r => r.includes('|'))
    if (rows.length < 2) return tableBlock
    const headers = rows[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('')
    const bodyRows = rows.slice(1).filter(r => !/^\|?\s*[-:]+\s*\|/.test(r))
    const body = bodyRows.map(r => {
      const cells = r.split('|').filter(c => c.trim())
      return `<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`
    }).join('')
    return `<table><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table>`
  })
  html = html.split('\n\n').map((para) => {
    const trimmed = para.trim()
    if (!trimmed) return ''
    if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') || trimmed.startsWith('<pre') || trimmed.startsWith('<li') || trimmed === '<hr>' || trimmed.startsWith('<hr ')) return trimmed
    return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`
  }).filter(p => p && p !== '<p><br></p>' && p !== '<p></p>').join('\n')
  return html
}