import type { Paper } from '@/types'

/** Same canonical keys as backend daily_paper_identity_sig, including unknown years. */
export function paperIdentity(paper: Pick<Paper, 'arxiv_id' | 'doi' | 'title' | 'year'>): string {
  const arxiv = String(paper.arxiv_id || '').trim().replace(/v\d+$/, '').toLowerCase()
  if (arxiv) return `arxiv:${arxiv}`
  const doi = String(paper.doi || '').trim().toLowerCase()
  if (doi) return `doi:${doi}`
  const year = Number(paper.year || 0)
  return `ty:${String(paper.title || '').trim().toLowerCase()}|${Number.isFinite(year) ? Math.trunc(year) : 0}`
}
