<template>
  <div class="markdown-renderer">
    <template v-for="(block, i) in contentBlocks" :key="i">
      <QuizWidget
        v-if="block.type === 'quiz'"
        :data="block.data"
        @answer="(correct: boolean) => onQuizAnswer(i, correct)"
      />
      <CodeRunner
        v-else-if="block.type === 'code'"
        :code="block.code"
        :language="block.language"
      />
      <div v-else class="markdown-body" v-html="block.html"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import QuizWidget from './QuizWidget.vue'
import CodeRunner from './CodeRunner.vue'

const props = withDefaults(defineProps<{
  content: string
  autoCollapse?: boolean
  collapseDepth?: number
}>(), {
  autoCollapse: true,
  collapseDepth: 2,
})

// ── marked config ──
marked.setOptions({ gfm: true, breaks: true })

const renderer = new marked.Renderer()

renderer.code = function({ text, lang }: { text: string; lang?: string }) {
  const code = typeof text === 'object' ? (text as any).text || '' : text
  const language = typeof text === 'object' ? (text as any).lang || lang : lang
  if (language && hljs.getLanguage(language)) {
    try {
      const h = hljs.highlight(code, { language }).value
      return `<pre class="hljs"><code class="language-${language}">${h}</code></pre>`
    } catch (_) { /* fallback */ }
  }
  try {
    const h = hljs.highlightAuto(code).value
    return `<pre class="hljs"><code>${h}</code></pre>`
  } catch (_) {
    return `<pre class="hljs"><code>${code}</code></pre>`
  }
}

const origHtml = renderer.html.bind(renderer)
renderer.html = function(token: { text: string }) {
  const html = typeof token === 'string' ? token : token.text
  if (html.includes('<details')) return html
  return origHtml(token)
}

marked.use({ renderer })

// ── types ──
interface QuizBlock { type: 'quiz'; data: { question: string; options: string[]; correct: number; explanation: string } }
interface CodeBlock { type: 'code'; code: string; language: string }
interface HtmlBlock { type: 'html'; html: string }
type ContentBlock = HtmlBlock | QuizBlock | CodeBlock

// ── auto-wrap ## headings into <details> ──
function autoWrapDetails(md: string): string {
  if (!props.autoCollapse || !md) return md
  const pat = new RegExp(`^#{${props.collapseDepth}} +`, 'm')
  const lines = md.split('\n')
  const secs: { h?: string; body: string[] }[] = []
  let cur: { h?: string; body: string[] } = { body: [] }

  for (const line of lines) {
    if (pat.test(line)) {
      if (cur.body.length > 0 || cur.h !== undefined) secs.push(cur)
      cur = { h: line.replace(/^#{2,4} +/, '').trim(), body: [] }
    } else {
      cur.body.push(line)
    }
  }
  if (cur.body.length > 0 || cur.h) secs.push(cur)

  return secs.map((s, i) => {
    const b = s.body.join('\n').trim()
    if (!b) return s.h ? `## ${s.h}` : ''
    return s.h
      ? `<details class="md-collapse" ${i === 0 ? 'open' : ''} open>\n<summary>${s.h}</summary>\n\n${b}\n\n</details>`
      : b
  }).filter(Boolean).join('\n\n')
}

// ── extract ```quiz and ```python blocks ──
const QUIZ_RE = /```quiz\s*\n([\s\S]*?)```/g
const CODE_RE = /```(python|javascript|typescript|bash|sh)\s*\n([\s\S]*?)```/g

interface ExtractedCode { index: number; code: string; language: string; fullMatch: string }

function sanitizeHtml(raw: string): string {
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ['pre', 'code', 'details', 'summary'],
    ADD_ATTR: ['class', 'open'],
  })
}

const contentBlocks = computed(() => {
  const blocks: ContentBlock[] = []
  let md = props.content || ''
  if (!md) return blocks

  // ---- Step 1: Extract quiz blocks ----
  const quizBlocks: { start: number; end: number; data: QuizBlock['data'] }[] = []
  QUIZ_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = QUIZ_RE.exec(md)) !== null) {
    try {
      const d = JSON.parse(m[1].trim())
      quizBlocks.push({
        start: m.index,
        end: m.index + m[0].length,
        data: { question: d.question, options: d.options, correct: d.correct ?? 0, explanation: d.explanation },
      })
    } catch {
      // parse failed, leave as-is
    }
  }

  // ---- Step 2: Extract runnable code blocks ----
  const codeBlocks: { start: number; end: number; code: string; language: string }[] = []
  CODE_RE.lastIndex = 0
  while ((m = CODE_RE.exec(md)) !== null) {
    // Skip if inside a quiz block
    const insideQuiz = quizBlocks.some(q => m!.index >= q.start && m!.index < q.end)
    if (!insideQuiz) {
      codeBlocks.push({
        start: m.index,
        end: m.index + m[0].length,
        code: m[2].trim(),
        language: m[1],
      })
    }
  }

  // ---- Step 3: Merge all regions and split into segments ----
  const regions: { start: number; end: number; type: string; data?: any }[] = [
    ...quizBlocks.map(q => ({ start: q.start, end: q.end, type: 'quiz', data: q.data })),
    ...codeBlocks.map(c => ({ start: c.start, end: c.end, type: 'code', data: { code: c.code, language: c.language } })),
  ].sort((a, b) => a.start - b.start)

  let cursor = 0
  for (const region of regions) {
    // Text before this region
    if (region.start > cursor) {
      const before = md.slice(cursor, region.start)
      if (before.trim()) {
        const html = marked.parse(autoWrapDetails(before)) as string
        blocks.push({ type: 'html', html: sanitizeHtml(html) })
      }
    }
    // The region itself
    if (region.type === 'quiz') {
      blocks.push({ type: 'quiz', data: region.data })
    } else if (region.type === 'code') {
      blocks.push({ type: 'code', code: region.data.code, language: region.data.language })
    }
    cursor = region.end
  }

  // Remaining text
  if (cursor < md.length) {
    const rest = md.slice(cursor)
    if (rest.trim()) {
      const html = marked.parse(autoWrapDetails(rest)) as string
      blocks.push({ type: 'html', html: sanitizeHtml(html) })
    }
  }

  return blocks
})

function onQuizAnswer(_i: number, _correct: boolean) {
  // future: track answers for score summary
}
</script>

<style scoped>
.markdown-renderer { width: 100%; }
.markdown-body {
  font-size: 14px;
  line-height: 1.7;
  word-wrap: break-word;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 16px; margin-bottom: 8px;
  font-weight: 600; line-height: 1.25;
}
.markdown-body :deep(h1) { font-size: 1.5em; }
.markdown-body :deep(h2) { font-size: 1.3em; }
.markdown-body :deep(h3) { font-size: 1.15em; }
.markdown-body :deep(h4) { font-size: 1em; }
.markdown-body :deep(p) { margin-top: 0; margin-bottom: 12px; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin-top: 0; margin-bottom: 12px; padding-left: 24px; }
.markdown-body :deep(li) { margin-bottom: 4px; }
.markdown-body :deep(li + li) { margin-top: 4px; }
.markdown-body :deep(pre) { margin: 0 0 12px; padding: 12px 16px; font-size: 12px; line-height: 1.5; background: #1e1e1e; border-radius: 8px; overflow-x: auto; }
.markdown-body :deep(code) { font-family: 'SF Mono','Fira Code','Cascadia Code',Consolas,monospace; }
.markdown-body :deep(:not(pre) > code) { padding: 2px 6px; font-size: .9em; background: rgba(0,0,0,.06); border-radius: 4px; color: #e83e8c; }
.markdown-body :deep(blockquote) { margin: 0 0 12px; padding: 8px 16px; border-left: 4px solid #667eea; background: rgba(102,126,234,.05); border-radius: 0 8px 8px 0; }
.markdown-body :deep(blockquote p) { margin-bottom: 0; }
.markdown-body :deep(table) { width: 100%; margin: 0 0 12px; border-collapse: collapse; border: 1px solid #e1e4e8; border-radius: 8px; overflow: hidden; }
.markdown-body :deep(th), .markdown-body :deep(td) { padding: 8px 12px; border: 1px solid #e1e4e8; text-align: left; }
.markdown-body :deep(th) { font-weight: 600; background: #f6f8fa; }
.markdown-body :deep(tr:nth-child(even)) { background: #f6f8fa; }
.markdown-body :deep(a) { color: #667eea; text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(hr) { margin: 16px 0; border: 0; border-top: 1px solid #e1e4e8; }
.markdown-body :deep(img) { max-width: 100%; height: auto; border-radius: 8px; }

/* Details collapsible */
.markdown-body :deep(details.md-collapse) { margin: 8px 0; border: 1px solid #e4e7ed; border-radius: 10px; overflow: hidden; background: #fafbfc; transition: all .2s; }
.markdown-body :deep(details.md-collapse[open]) { background: #fff; border-color: #d0d5e0; box-shadow: 0 1px 4px rgba(0,0,0,.04); }
.markdown-body :deep(details.md-collapse summary) { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-weight: 600; font-size: 14px; color: #1a1a1a; cursor: pointer; user-select: none; list-style: none; }
.markdown-body :deep(details.md-collapse summary::before) { content: '▶'; font-size: 10px; color: #999; transition: transform .2s; flex-shrink: 0; }
.markdown-body :deep(details.md-collapse[open] summary::before) { transform: rotate(90deg); }
.markdown-body :deep(details.md-collapse summary::-webkit-details-marker) { display: none; }
.markdown-body :deep(details.md-collapse summary::marker) { display: none; content: ''; }
.markdown-body :deep(details.md-collapse summary:hover) { background: rgba(0,0,0,.02); }
.markdown-body :deep(details.md-collapse > :not(summary)) { padding: 0 14px 10px 30px; animation: fade-in .25s ease; }
@keyframes fade-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
.markdown-body :deep(details.md-collapse:first-of-type) { border-color: #d0d5e0; background: #fff; }
</style>
