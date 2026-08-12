import type {
  MovieDetailResponse,
  MovieListResponse,
} from '../types'
import { apiFetch } from './client'

export function searchMovies(q: string, year?: number): Promise<MovieListResponse> {
  const params = new URLSearchParams({ q })
  if (year != null) params.set('year', String(year))
  return apiFetch<MovieListResponse>(`/api/movies/search?${params}`, {}, 30_000)
}

export interface DiscoverParams {
  with_genres?: string
  year?: number
  year_gte?: number
  year_lte?: number
  max_runtime?: number
  with_original_language?: string
  sort_by?: string
  page?: number
}

export function discoverMovies(params: DiscoverParams = {}): Promise<MovieListResponse> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '') continue
    qs.set(k, String(v))
  }
  const suffix = qs.toString() ? `?${qs}` : ''
  return apiFetch<MovieListResponse>(`/api/movies/discover${suffix}`, {}, 30_000)
}

export function getMovieDetail(id: number): Promise<MovieDetailResponse> {
  return apiFetch<MovieDetailResponse>(`/api/movies/${id}`, {}, 30_000)
}
