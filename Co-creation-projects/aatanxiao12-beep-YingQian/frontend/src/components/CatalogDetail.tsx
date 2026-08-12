import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getMovieDetail } from '../api/movies'
import type { CandidateMovie, MovieDetail } from '../types'
import { formatRating, formatRuntime } from '../lib/format'
import { isSeen, toggleSeen, type SeenEntry } from '../lib/seen'
import { DetailFacts } from './DetailFacts'

interface CatalogDetailProps {
  movie: CandidateMovie
  onClose: () => void
  onSeenChange: (list: SeenEntry[]) => void
}

export function CatalogDetail({ movie, onClose, onSeenChange }: CatalogDetailProps) {
  const navigate = useNavigate()
  const [detail, setDetail] = useState<MovieDetail | CandidateMovie>(movie)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seen, setSeen] = useState(() => isSeen(movie.id))

  useEffect(() => {
    let cancelled = false
    setDetail(movie)
    setSeen(isSeen(movie.id))
    setLoading(true)
    setError(null)

    void getMovieDetail(movie.id)
      .then((res) => {
        if (cancelled || !res.data) return
        setDetail(res.data)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : '详情加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [movie])

  function handleToggleSeen() {
    const next = toggleSeen({
      id: detail.id,
      title: detail.title,
      year: detail.year,
    })
    setSeen(next.some((e) => e.id === detail.id))
    onSeenChange(next)
  }

  function handleRecommendWithGenre() {
    const genre = detail.genres[0]
    navigate('/', {
      state: genre
        ? { prefillGenres: [genre], hint: `已带入类型「${genre}」，可继续调整偏好` }
        : { hint: '请手动选择类型后再生成片单' },
    })
  }

  const rating = formatRating(detail.rating)
  const runtime = formatRuntime(detail.runtime)
  const rich = 'directors' in detail ? (detail as MovieDetail) : null

  return (
    <aside className="catalog-detail" aria-label="影片详情">
      <div className="catalog-detail__toolbar">
        <button type="button" className="btn btn--ghost btn--compact" onClick={onClose}>
          关闭
        </button>
      </div>

      <div className="catalog-detail__layout">
        <div className="catalog-detail__poster">
          {detail.poster_url ? (
            <img src={detail.poster_url} alt="" />
          ) : (
            <div className="catalog-tile__fallback">{detail.title.slice(0, 1)}</div>
          )}
        </div>

        <div className="catalog-detail__body">
          <h2>{detail.title}</h2>
          <p className="catalog-detail__meta">
            {[detail.year, rating && `评分 ${rating}`, runtime]
              .filter(Boolean)
              .join(' · ')}
          </p>
          {detail.genres.length > 0 && (
            <ul className="catalog-detail__genres">
              {detail.genres.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          )}

          {loading && <p className="muted">正在拉取完整信息…</p>}
          {error && <p className="error-text">{error}</p>}
          {!loading && rich?.tagline && (
            <p className="detail-tagline">{rich.tagline}</p>
          )}
          {!loading && detail.overview && (
            <p className="catalog-detail__overview">{detail.overview}</p>
          )}
          {!loading && !detail.overview && !error && (
            <p className="muted">暂无简介</p>
          )}
          {!loading && rich && <DetailFacts detail={rich} />}
          {!loading && rich?.tmdb_url && (
            <p className="detail-link">
              <a href={rich.tmdb_url} target="_blank" rel="noreferrer">
                在 TMDB 查看
              </a>
            </p>
          )}

          <div className="catalog-detail__actions">
            <button
              type="button"
              className={seen ? 'btn btn--primary btn--compact' : 'btn btn--ghost btn--compact'}
              onClick={handleToggleSeen}
            >
              {seen ? '已标记已看' : '标记已看'}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--compact"
              onClick={handleRecommendWithGenre}
            >
              用此类型去推荐
            </button>
            <Link to="/" className="btn btn--ghost btn--compact">
              返回智能推荐
            </Link>
          </div>
        </div>
      </div>
    </aside>
  )
}
