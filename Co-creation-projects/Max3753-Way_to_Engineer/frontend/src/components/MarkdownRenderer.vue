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
      <div v-else-if="block.type === 'exercise'" class="exercise-card">
        <div class="ec-header">
          <span class="ec-lang">{{ block.language }}</span>
          <span class="ec-badge">📝 代码练习</span>
        </div>
        <pre class="ec-preview"><code>{{ block.code }}</code></pre>
        <div class="ec-actions">
          <button class="ec-open-btn" @click="$emit('exerciseDetected', { code: block.code, language: block.language })">
            📂 在编辑器中打开
          </button>
        </div>
      </div>
      <div v-else class="markdown-body" v-html="block.html"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
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
interface ExerciseBlock { type: 'exercise'; code: string; language: string }
interface HtmlBlock { type: 'html'; html: string }
type ContentBlock = HtmlBlock | QuizBlock | CodeBlock | ExerciseBlock

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
    if (!s.h) return b
    // 第一个折叠块默认展开，其余收起
    const openAttr = i === 0 ? ' open' : ''
    return `<details class="md-collapse"${openAttr}>\n<summary>${s.h}</summary>\n\n${b}\n\n</details>`
  }).filter(Boolean).join('\n\n')
}

// ── extract ```quiz / ```exercise:lang / ```lang blocks ──
const QUIZ_RE = /```quiz\s*\n([\s\S]*?)```/g
const EXERCISE_RE = /```exercise:(\w+)\s*\n([\s\S]*?)```/g
const CODE_RE = /```(python|javascript|typescript|html|css|bash|sh)\s*\n([\s\S]*?)```/g

interface ExtractedCode { index: number; code: string; language: string; fullMatch: string }

function sanitizeHtml(raw: string): string {
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ['pre', 'code', 'details', 'summary'],
    ADD_ATTR: ['class', 'open'],
  })
}

/**
 * Heuristic: infer correct answer index from quiz explanation text.
 * LLM often outputs correct=0 due to training data bias, even when
 * the explanation clearly identifies a different option as correct.
 * This detects contradictions and explicit mentions to fix the index.
 */
function inferCorrectFromExplanation(explanation: string, options: string[], llmCorrect: number): number | null {
  const letters = ['A', 'B', 'C', 'D']
  const optCount = options.length
  const exp = explanation.trim()

  // 1) Explicit positive mention: "X 是正确答案" / "X 正确" / "正确: X" / "选项X"
  for (let i = 0; i < optCount; i++) {
    const letter = letters[i]
    const posPatterns = [
      new RegExp(`${letter}\\s*(?:是正确答案|正确选项|符合题意|符合|可以|应该选|正确)`),
      new RegExp(`(?:正确答案|正确选项|应选|选择|推荐)\\s*[:：]?\\s*[（(]?${letter}[）)]?`),
      new RegExp(`[（(]${letter}[）)]\\s*(?:正确|符合)`),
    ]
    for (const pat of posPatterns) {
      if (pat.test(exp)) return i
    }
  }

  // 2) Contradiction: LLM says correct=0 but explanation says A is wrong
  if (llmCorrect === 0) {
    // Broader negative detection: include "描述的是...的行为","是指" etc.
    const negPattern = /[（(]?([A-D])[）)]?\s*(?:错误|不对|不符合|缺少|不是|缺少引号|报错|描述的是|的行为|是指)/
    const negMatch = exp.match(negPattern)
    if (negMatch) {
      const wrongLetter = negMatch[1]
      const wrongIdx = wrongLetter.charCodeAt(0) - 65
      if (wrongIdx === 0) {
        // A is explicitly wrong, so correct is not 0. Find right one.
        // Check if explanation starts with an option's text (strong signal)
        for (let i = 1; i < optCount; i++) {
          const optText = options[i].replace(/^[A-D][.、．\s]+/, '').trim()
          if (optText.length >= 4 && exp.startsWith(optText)) {
            // Verify this option is NOT marked as wrong
            const alsoNeg = new RegExp(`[（(]?${letters[i]}[）)]?\\s*(?:错误|不对|不符合|缺少|不是|缺少引号|报错|描述的是|的行为|是指)`)
            if (!alsoNeg.test(exp)) return i
          }
        }
        // Fallback: find first option not explicitly negated
        for (let i = 1; i < optCount; i++) {
          const alsoNeg = new RegExp(`[（(]?${letters[i]}[）)]?\\s*(?:错误|不对|不符合|缺少|不是|缺少引号|报错|描述的是|的行为|是指)`)
          if (!alsoNeg.test(exp)) return i
        }
        return 1
      }
    }
  }

  return null // no override
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
      const raw = m[1].trim()
      const d = JSON.parse(raw)
      // validate + fallback: accept quizes even with partial data
      const hasQuestion = typeof d.question === 'string' && d.question.trim().length > 0
      const hasOptions = Array.isArray(d.options) && d.options.length >= 2
      const hasExplanation = typeof d.explanation === 'string' && d.explanation.trim().length > 0
      if (!hasQuestion || !hasOptions) {
        // missing essential fields -> skip, renders as plain text
        continue
      }
      // coerce correct to number (AI sometimes outputs string like "2" instead of 2)
      let rawCorrect = d.correct
      if (typeof rawCorrect === 'string') {
        rawCorrect = Number(rawCorrect)
      }
      const hasCorrect = typeof rawCorrect === 'number' && !Number.isNaN(rawCorrect)
      // clamp correct index to valid range
      let correctIdx = hasCorrect ? Math.round(rawCorrect) : 0
      if (correctIdx < 0 || correctIdx >= d.options.length) {
        correctIdx = 0
      }
      // ── heuristic: validate correctIdx against explanation ──
      // LLM often defaults to correct=0 even when answer is elsewhere.
      // Cross-check: if explanation mentions an option letter as "wrong" but
      // correctIdx points to it, OR explanation explicitly names the right option, override.
      if (hasExplanation && d.options.length >= 2) {
        const inferred = inferCorrectFromExplanation(d.explanation, d.options, correctIdx)
        if (inferred !== null && inferred !== correctIdx) {
          correctIdx = inferred
        }
      }
      quizBlocks.push({
        start: m.index,
        end: m.index + m[0].length,
        data: {
          question: d.question.trim(),
          options: d.options,
          correct: correctIdx,
          explanation: hasExplanation ? d.explanation.trim() : '',
          code: typeof d.code === 'string' ? d.code.trim() : undefined,
        },
      })
    } catch {
      // parse failed, leave as-is (renders as plain markdown)
    }
  }

  // ---- Step 2: Extract exercise code blocks (editable + submit) ----
  const exerciseBlocks: { start: number; end: number; code: string; language: string }[] = []
  EXERCISE_RE.lastIndex = 0
  while ((m = EXERCISE_RE.exec(md)) !== null) {
    const insideQuiz = quizBlocks.some(q => m!.index >= q.start && m!.index < q.end)
    if (!insideQuiz) {
      exerciseBlocks.push({
        start: m.index,
        end: m.index + m[0].length,
        code: m[2].trim(),
        language: m[1],
      })
    }
  }

  // ---- Step 3: Extract runnable code blocks ----
  const codeBlocks: { start: number; end: number; code: string; language: string; exercise?: boolean }[] = []
  CODE_RE.lastIndex = 0
  while ((m = CODE_RE.exec(md)) !== null) {
    // Skip if inside a quiz or exercise block
    const insideQuiz = quizBlocks.some(q => m!.index >= q.start && m!.index < q.end)
    const insideExercise = exerciseBlocks.some(e => m!.index >= e.start && m!.index < e.end)
    if (!insideQuiz && !insideExercise) {
      codeBlocks.push({
        start: m.index,
        end: m.index + m[0].length,
        code: m[2].trim(),
        language: m[1],
      })
    }
  }

  // ---- Step 4: Merge all regions and split into segments ----
  const regions: { start: number; end: number; type: string; data?: any }[] = [
    ...quizBlocks.map(q => ({ start: q.start, end: q.end, type: 'quiz', data: q.data })),
    ...exerciseBlocks.map(c => ({ start: c.start, end: c.end, type: 'exercise', data: { code: c.code, language: c.language } })),
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
    } else if (region.type === 'exercise') {
      blocks.push({ type: 'exercise', code: region.data.code, language: region.data.language })
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

const emit = defineEmits<{
  quizResult: [result: { total: number; correct: number }]
  exerciseDetected: [data: { code: string; language: string }]
  contentMeta: [meta: { quizCount: number; exerciseCount: number }]
}>()

const quizResults = reactive<Record<number, boolean>>({})

// Reset tracking when content changes (new agent response)
watch(() => props.content, (newContent) => {
  for (const key of Object.keys(quizResults)) {
    delete quizResults[key]
  }
  
  // Emit content meta for quiz/exercise tracking
  if (newContent) {
    const quizCount = (newContent.match(/```quiz\s*\n/g) || []).length
    const exerciseCount = (newContent.match(/```exercise:\w+\s*\n/g) || []).length
    emit('contentMeta', { quizCount, exerciseCount })
  }
}, { immediate: true })

function onQuizAnswer(index: number, correct: boolean) {
  quizResults[index] = correct

  const total = contentBlocks.value.filter(b => b.type === 'quiz').length
  const answered = Object.keys(quizResults).length
  if (answered >= total && total > 0) {
    const correctCount = Object.values(quizResults).filter(Boolean).length
    emit('quizResult', { total, correct: correctCount })
  }
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

/* Exercise Card */
.exercise-card {
  margin: 12px 0;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  overflow: hidden;
  background: #fafbfc;
}
.ec-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f0f2f5;
  border-bottom: 1px solid #e4e7ed;
}
.ec-lang {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ec-badge {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
}
.ec-preview {
  margin: 0;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.5;
  background: #1e1e1e;
  color: #c9d1d9;
  max-height: 180px;
  overflow-y: auto;
  font-family: 'SF Mono','Fira Code','Cascadia Code',Consolas,monospace;
}
.ec-preview code {
  font-family: inherit;
  white-space: pre;
}
.ec-actions {
  padding: 8px 14px;
  background: #fafbfc;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
}
.ec-open-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  background: #667eea;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.ec-open-btn:hover {
  background: #5a6fd6;
  transform: translateY(-1px);
}
</style>
