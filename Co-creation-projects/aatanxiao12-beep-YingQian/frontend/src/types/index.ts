/** TypeScript 契约，对齐 backend/app/models/schemas.py（D4） */

export type Mood = '放松' | '欢乐' | '虐心' | '烧脑' | '紧张刺激' | '温馨'
export type PartyType = '独自' | '情侣' | '家庭' | '朋友'
export type RegionPreference = '华语' | '好莱坞' | '日韩' | '欧洲' | '不限'
export type YearPreference = '不限' | '近5年' | '近10年' | '经典'

export interface RecommendRequest {
  mood: Mood
  party_type: PartyType
  genres: string[]
  max_runtime_minutes: number | null
  region_preference: RegionPreference
  year_preference: YearPreference
  exclude_titles: string[]
  spoilers_ok: boolean
  free_text: string
  exclude_ids: number[]
  /** 换一批时回传，后端跳过画像 Agent */
  taste_profile?: TasteProfile | null
}

export interface TasteProfile {
  summary: string
  genre_hints: string[]
  language_hints: string[]
  avoid: string[]
  discover_notes: string
}

export interface CandidateMovie {
  id: number
  title: string
  year: number | null
  genres: string[]
  runtime: number | null
  rating: number | null
  poster_url: string | null
  overview: string | null
}

export interface MovieDetail extends CandidateMovie {
  tagline: string | null
  original_title: string | null
  vote_count: number | null
  original_language: string | null
  countries: string[]
  directors: string[]
  cast: string[]
  tmdb_url: string | null
}

export interface MovieCard {
  id: number
  title: string
  year: number | null
  genres: string[]
  runtime: number | null
  rating: number | null
  poster_url: string | null
  why: string
  vibe_tags: string[]
  caution: string | null
  overview_safe: string
}

export interface RecommendResult {
  playlist_name: string
  profile_summary: string
  movies: MovieCard[]
  is_fallback: boolean
  taste_profile?: TasteProfile | null
}

export interface RecommendResponse {
  success: boolean
  message: string
  data: RecommendResult | null
}

export interface MovieListResponse {
  success: boolean
  message: string
  data: CandidateMovie[]
}

export interface MovieDetailResponse {
  success: boolean
  message: string
  data: MovieDetail | null
}

export const MOODS: Mood[] = ['放松', '欢乐', '虐心', '烧脑', '紧张刺激', '温馨']
export const PARTY_TYPES: PartyType[] = ['独自', '情侣', '家庭', '朋友']
export const REGIONS: RegionPreference[] = ['不限', '华语', '好莱坞', '日韩', '欧洲']
export const YEARS: YearPreference[] = ['不限', '近5年', '近10年', '经典']
export const GENRE_OPTIONS = [
  '剧情',
  '喜剧',
  '爱情',
  '科幻',
  '动画',
  '悬疑',
  '纪录',
  '动作',
  '冒险',
  '恐怖',
  '惊悚',
  '奇幻',
] as const
export const RUNTIME_OPTIONS: { label: string; value: number | null }[] = [
  { label: '不限', value: null },
  { label: '90 分钟内', value: 90 },
  { label: '120 分钟内', value: 120 },
  { label: '150 分钟内', value: 150 },
]

export const DEMO_REQUEST: RecommendRequest = {
  mood: '放松',
  party_type: '独自',
  genres: ['剧情', '喜剧'],
  max_runtime_minutes: 120,
  region_preference: '不限',
  year_preference: '近10年',
  exclude_titles: [],
  spoilers_ok: false,
  free_text: '不要太沉重',
  exclude_ids: [],
}

export const PROGRESS_STAGES = [
  '分析口味',
  '检索片库',
  '生成推荐',
  '校验',
] as const

export type ProgressStage = (typeof PROGRESS_STAGES)[number]

export interface SessionPayload {
  request: RecommendRequest
  result: RecommendResult
  message: string
}
