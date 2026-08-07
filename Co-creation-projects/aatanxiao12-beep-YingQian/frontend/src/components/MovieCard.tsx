import { useState } from 'react'
import type { MovieCard as MovieCardType, MovieDetail } from '../types'
import { getMovieDetail } from '../api/movies'
import { DetailFacts } from './DetailFacts'
import { formatRating, formatRuntime } from '../lib/format'

interface MovieCardProps {
  movie: MovieCardType
  index?: number
}

export function MovieCardView({ movie, index = 0 }: MovieCardProps) {
  const [runtime, setRuntime] = useState(movie.runtime)
  const [overview, setOverview] = useState(movie.overview_safe)
  const [detail, setDetail] = useState<MovieDetail | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  async function handleToggle() {
    const next = !expanded
    setExpanded(next)
    if (!next || detail) return

    setLoadingDetail(true)
    setDetailError(null)
    try {
      const res = await getMovieDetail(movie.id)
      if (res.data) {
        setDetail(res.data)
        if (res.data.runtime != null) setRuntime(res.data.runtime)
        if (res.data.overview) setOverview(res.data.overview)
      }
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : '详情加载失败')
    } finally {
      setLoadingDetail(false)
    }
  }

  const rating = formatRating(detail?.rating ?? movie.rating)
  const runtimeLabel = formatRuntime(runtime)

  return (
    <article
      className="movie-card"
      style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
    >
      <button
        type="button"
        className="movie-card__hit"
        onClick={() => void handleToggle()}
        aria-expanded={expanded}
      >
        <div className="movie-card__poster">
          {movie.poster_url ? (
            <img src={movie.poster_url} alt="" loading="lazy" />
          ) : (
            <div className="movie-card__poster-fallback">{movie.title.slice(0, 1)}</div>
          )}
        </div>
        <div className="movie-card__body">
          <header className="movie-card__header">
            <h3>{movie.title}</h3>
            <div className="movie-card__meta">
              {movie.year != null && <span>{movie.year}</span>}
              {rating && <span>评分 {rating}</span>}
              {runtimeLabel && <span>{runtimeLabel}</span>}
              {movie.genres.slice(0, 3).map((g) => (
                <span key={g}>{g}</span>
              ))}
            </div>
          </header>
          {movie.why && <p className="movie-card__why">{movie.why}</p>}
          {movie.vibe_tags.length > 0 && (
            <ul className="movie-card__tags">
              {movie.vibe_tags.map((tag) => (
                <li key={tag}>{tag}</li>
              ))}
            </ul>
          )}
          {movie.caution && (
            <p className="movie-card__caution">适看提示：{movie.caution}</p>
          )}
          <p className="movie-card__more muted">
            {expanded ? '收起详情' : '展开详情'}
          </p>
        </div>
      </button>

      {expanded && (
        <div className="movie-card__detail">
          {loadingDetail && <p className="muted">正在加载详情…</p>}
          {detailError && <p className="error-text">{detailError}</p>}
          {!loadingDetail && detail?.tagline && (
            <p className="detail-tagline">{detail.tagline}</p>
          )}
          {!loadingDetail && overview && (
            <p className="detail-overview">{overview}</p>
          )}
          {!loadingDetail && detail && <DetailFacts detail={detail} />}
          {!loadingDetail && !overview && !detailError && (
            <p className="muted">暂无简介</p>
          )}
          {!loadingDetail && detail?.tmdb_url && (
            <p className="detail-link">
              <a href={detail.tmdb_url} target="_blank" rel="noreferrer">
                在 TMDB 查看
              </a>
            </p>
          )}
        </div>
      )}
    </article>
  )
}
