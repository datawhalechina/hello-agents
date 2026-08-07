import type { CandidateMovie } from '../types'
import { formatRating } from '../lib/format'

interface CatalogTileProps {
  movie: CandidateMovie
  index: number
  selected?: boolean
  seen?: boolean
  onSelect: (movie: CandidateMovie) => void
}

export function CatalogTile({
  movie,
  index,
  selected,
  seen,
  onSelect,
}: CatalogTileProps) {
  const rating = formatRating(movie.rating)

  return (
    <button
      type="button"
      className={
        selected
          ? 'catalog-tile is-selected'
          : 'catalog-tile'
      }
      style={{ animationDelay: `${Math.min(index, 12) * 40}ms` }}
      onClick={() => onSelect(movie)}
    >
      <div className="catalog-tile__poster">
        {movie.poster_url ? (
          <img src={movie.poster_url} alt="" loading="lazy" />
        ) : (
          <div className="catalog-tile__fallback">{movie.title.slice(0, 1)}</div>
        )}
        {seen && <span className="catalog-tile__badge">已看</span>}
      </div>
      <div className="catalog-tile__meta">
        <span className="catalog-tile__title">{movie.title}</span>
        <span className="catalog-tile__sub">
          {movie.year ?? '—'}
          {rating ? ` · ${rating}` : ''}
        </span>
      </div>
    </button>
  )
}
