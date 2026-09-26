import type { Paper } from '@/types'
const TITLE_STOP = new Set([
  'with',
  'from',
  'that',
  'this',
  'these',
  'those',
  'based',
  'using',
  'via',
  'for',
  'and',
  'the',
  'are',
  'was',
  'were',
  'learning',
  'deep',
  'neural',
  'network',
  'networks',
  'approach',
  'towards',
  'large',
  'small',
  'models',
  'model',
  'data',
  'method',
  'methods',
  'paper',
  'papers',
  'arxiv',
  'survey',
  'review',
  'efficient',
  'novel',
  'improved',
  'study',
  'studies',
  'analysis',
  'task',
  'tasks',
  'language',
  'benchmark',
  'benchmarks',
  'performance',
  'training',
  'inference',
])
function englishContentWordsFromTitle(title: string): string[] {
  const t = (title || '').trim()
  if (!t) return []
  const lower = t.toLowerCase().replace(/[^a-z0-9]+/g, ' ')
  const out: string[] = []
  for (const w of lower.split(/\s+/)) {
    if (w.length >= 4 && !TITLE_STOP.has(w)) out.push(w)
  }
  return out
}
function chineseTitleChunks(title: string): string[] {
  const t = (title || '').trim()
  if (!t) return []
  return [...t.matchAll(/[\u4e00-\u9fff]{3,8}/g)].map((m) => m[0])
}
function englishPhrasesFromWords(words: string[]): string[] {
  const phrases: string[] = []
  const n = words.length
  for (let i = 0; i <= n - 3; i++) phrases.push(`${words[i]} ${words[i + 1]} ${words[i + 2]}`)
  for (let i = 0; i <= n - 2; i++) phrases.push(`${words[i]} ${words[i + 1]}`)
  for (const w of words) phrases.push(w)
  return phrases
}
function phraseWordCount(phrase: string): number {
  return phrase.includes(' ') ? phrase.split(/\s+/).length : 1
}
export function titleCoKeywordsFromPapers(papers: Paper[], limit = 5): string[] {
  const freq = new Map<string, number>()
  for (const p of papers) {
    const once = new Set<string>()
    const words = englishContentWordsFromTitle(p.title || '')
    for (const phrase of englishPhrasesFromWords(words)) {
      if (once.has(phrase)) continue
      once.add(phrase)
      freq.set(phrase, (freq.get(phrase) ?? 0) + 1)
    }
    for (const chunk of chineseTitleChunks(p.title || '')) {
      if (once.has(chunk)) continue
      once.add(chunk)
      freq.set(chunk, (freq.get(chunk) ?? 0) + 1)
    }
  }
  const NGRAM_WEIGHT = 1.35
  type Cand = { phrase: string; freq: number; n: number; score: number }
  const candidates: Cand[] = [...freq.entries()].map(([phrase, f]) => {
    const n = phraseWordCount(phrase)
    return { phrase, freq: f, n, score: f * (1 + NGRAM_WEIGHT * (n - 1)) }
  })
  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    if (b.n !== a.n) return b.n - a.n
    return b.phrase.length - a.phrase.length
  })
  const selected: string[] = []
  const coveredEnglishTokens = new Set<string>()
  for (const c of candidates) {
    if (selected.length >= limit) break
    if (c.n === 1) {
      const isChinese = /[\u4e00-\u9fff]/.test(c.phrase)
      if (!isChinese && coveredEnglishTokens.has(c.phrase)) continue
    }
    selected.push(c.phrase)
    if (c.n > 1) {
      for (const tok of c.phrase.split(/\s+/)) {
        if (/^[a-z]+$/.test(tok)) coveredEnglishTokens.add(tok)
      }
    }
  }
  return selected
}