import { post } from './http'
import type { RagQueryIn, RagQueryOut } from '@/types'

export function ragQuery(payload: RagQueryIn): Promise<RagQueryOut> {
  return post<RagQueryOut>('/rag/query', payload)
}
