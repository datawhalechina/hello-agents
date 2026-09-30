import { post } from './http'
import type { TranslateIn, TranslateOut } from '@/types'

export function translateText(payload: TranslateIn): Promise<TranslateOut> {
  return post<TranslateOut>('/translate', payload)
}
