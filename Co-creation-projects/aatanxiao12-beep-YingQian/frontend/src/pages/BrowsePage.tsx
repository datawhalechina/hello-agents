import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { discoverMovies, searchMovies } from '../api/movies'
import { CatalogDetail } from '../components/CatalogDetail'
import { CatalogTile } from '../components/CatalogTile'
import { SiteFooter } from '../components/SiteFooter'
import { SiteNav } from '../components/SiteNav'
import { loadSeen, type SeenEntry } from '../lib/seen'
import type { CandidateMovie } from '../types'
import { GENRE_OPTIONS } from '../types'

type Mode = 'search' | 'discover'

const SORT_OPTIONS = [
  { value: 'popularity.desc', label: '热度' },
  { value: 'vote_average.desc', label: '评分' },
  { value: 'primary_release_date.desc', label: '新片优先' },
] as const

const LANG_OPTIONS = [
  { value: '', label: '语言不限' },
  { value: 'zh', label: '华语' },
  { value: 'en', label: '英语' },
  { value: 'ja', label: '日语' },
  { value: 'ko', label: '韩语' },
] as const

export function BrowsePage() {
  const [mode, setMode] = useState<Mode>('search')
  const [query, setQuery] = useState('')
  const [year, setYear] = useState('')
  const [genres, setGenres] = useState<string[]>([])
  const [lang, setLang] = useState('')
  const [sortBy, setSortBy] = useState<string>('popularity.desc')
  const [yearGte, setYearGte] = useState('')
  const [maxRuntime, setMaxRuntime] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<CandidateMovie[] | null>(null)
  const [selected, setSelected] = useState<CandidateMovie | null>(null)
  const [seenList, setSeenList] = useState<SeenEntry[]>(() => loadSeen())

  const runDiscover = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await discoverMovies({
        with_genres: genres.length ? genres.join(',') : undefined,
        year_gte: yearGte ? Number(yearGte) : undefined,
        max_runtime: maxRuntime ? Number(maxRuntime) : undefined,
        with_original_language: lang || undefined,
        sort_by: sortBy,
        page: 1,
      })
      setResults(res.data)
      setSelected(null)
    } catch (err) {
      setResults(null)
      setError(err instanceof Error ? err.message : '发现失败')
    } finally {
      setLoading(false)
    }
  }, [genres, yearGte, maxRuntime, lang, sortBy])

  useEffect(() => {
    if (mode !== 'discover') return
    void runDiscover()
  }, [mode, runDiscover])

  async function onSearchSubmit(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return

    setLoading(true)
    setError(null)
    try {
      const res = await searchMovies(q, year ? Number(year) : undefined)
      setResults(res.data)
      setSelected(null)
    } catch (err) {
      setResults(null)
      setError(err instanceof Error ? err.message : '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  function toggleGenre(g: string) {
    setGenres((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g].slice(0, 3),
    )
  }

  const seenIds = new Set(seenList.map((e) => e.id))

  return (
    <div className="page page--browse">
      <SiteNav active="browse" />

      <header className="browse-hero">
        <p className="section-kicker">片库</p>
        <h1 className="browse-title">找一部确认今晚</h1>
        <p className="browse-lead">
          搜片名，或按类型与年份筛选。点海报看详情，可标记已看。
        </p>
      </header>

      <div className="mode-tabs" role="tablist" aria-label="查询方式">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'search'}
          className={mode === 'search' ? 'mode-tab is-active' : 'mode-tab'}
          onClick={() => {
            setMode('search')
            setResults(null)
            setSelected(null)
            setError(null)
          }}
        >
          关键词搜索
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'discover'}
          className={mode === 'discover' ? 'mode-tab is-active' : 'mode-tab'}
          onClick={() => setMode('discover')}
        >
          条件发现
        </button>
      </div>

      {mode === 'search' ? (
        <form className="browse-toolbar" onSubmit={(e) => void onSearchSubmit(e)}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="片名、关键词，例如：盗梦空间"
            autoComplete="off"
            aria-label="搜索关键词"
          />
          <input
            type="number"
            className="browse-year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="年份"
            min={1900}
            max={2100}
            aria-label="上映年份"
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={loading || !query.trim()}
          >
            {loading ? '检索中…' : '搜索'}
          </button>
        </form>
      ) : (
        <div className="browse-filters">
          <div className="chip-row" aria-label="类型，最多三项">
            {GENRE_OPTIONS.map((g) => (
              <button
                key={g}
                type="button"
                className={genres.includes(g) ? 'chip is-on' : 'chip'}
                onClick={() => toggleGenre(g)}
              >
                {g}
              </button>
            ))}
          </div>
          <div className="browse-filters__row">
            <label>
              <span className="sr-only">起始年份</span>
              <input
                type="number"
                value={yearGte}
                onChange={(e) => setYearGte(e.target.value)}
                placeholder="起始年"
                min={1900}
                max={2100}
              />
            </label>
            <label>
              <span className="sr-only">片长上限</span>
              <select
                value={maxRuntime}
                onChange={(e) => setMaxRuntime(e.target.value)}
              >
                <option value="">片长不限</option>
                <option value="90">≤ 90 分</option>
                <option value="120">≤ 120 分</option>
                <option value="150">≤ 150 分</option>
              </select>
            </label>
            <label>
              <span className="sr-only">语言</span>
              <select value={lang} onChange={(e) => setLang(e.target.value)}>
                {LANG_OPTIONS.map((o) => (
                  <option key={o.value || 'any'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="sr-only">排序</span>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void runDiscover()}
              disabled={loading}
            >
              {loading ? '刷新中…' : '刷新结果'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      <div className={selected ? 'browse-split has-detail' : 'browse-split'}>
        <section className="catalog-grid" aria-label="影片列表">
          {loading && !results && <p className="muted">正在连接片库…</p>}
          {results && results.length === 0 && (
            <p className="muted">没有符合条件的影片，换个关键词或放宽筛选试试。</p>
          )}
          {results &&
            results.map((m, i) => (
              <CatalogTile
                key={m.id}
                movie={m}
                index={i}
                selected={selected?.id === m.id}
                seen={seenIds.has(m.id)}
                onSelect={setSelected}
              />
            ))}
          {!loading && results == null && mode === 'search' && (
            <p className="browse-empty muted">
              输入片名确认年份与海报，或切换到「条件发现」按口味逛一圈。
            </p>
          )}
        </section>

        {selected && (
          <CatalogDetail
            movie={selected}
            onClose={() => setSelected(null)}
            onSeenChange={setSeenList}
          />
        )}
      </div>

      {seenList.length > 0 && (
        <p className="browse-seen-hint muted">
          已标记 {seenList.length} 部已看；返回智能推荐时会自动带入排除列表。
        </p>
      )}

      <SiteFooter />
    </div>
  )
}
