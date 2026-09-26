import { get } from './http'
import type {
  GraphPaper,
  GraphPapersOut,
  GraphStats,
  GraphSubgraph,
  RelatedPapersOut
} from '@/types'

export function getGraphStats(): Promise<GraphStats> {
  return get<GraphStats>('/graph/stats')
}

export function getRelatedPapers(pmid: string, limit = 10): Promise<RelatedPapersOut> {
  return get<RelatedPapersOut>(`/graph/related/${encodeURIComponent(pmid)}?limit=${limit}`)
}

export function getSubgraph(pmid: string, limit = 10): Promise<GraphSubgraph> {
  return get<GraphSubgraph>(`/graph/subgraph/${encodeURIComponent(pmid)}?limit=${limit}`)
}

export function getGraphPaper(pmid: string): Promise<GraphPaper> {
  return get<GraphPaper>(`/graph/paper/${encodeURIComponent(pmid)}`)
}

export function getGraphPapers(limit = 20): Promise<GraphPapersOut> {
  return get<GraphPapersOut>(`/graph/papers?limit=${limit}`)
}
