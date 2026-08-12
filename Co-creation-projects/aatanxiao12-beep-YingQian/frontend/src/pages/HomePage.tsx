import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { postRecommend } from '../api/recommend'
import { BRAND_NAME, BRAND_TAGLINE } from '../brand'
import { PreferenceForm } from '../components/PreferenceForm'
import { ProgressOverlay } from '../components/ProgressOverlay'
import { SiteFooter } from '../components/SiteFooter'
import { SiteNav } from '../components/SiteNav'
import { loadSeen } from '../lib/seen'
import { saveSession } from '../lib/session'
import type { RecommendRequest } from '../types'
import { PROGRESS_STAGES } from '../types'

const STAGE_INTERVAL_MS = 4_500

export function HomePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [stageIndex, setStageIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [hint, setHint] = useState<string | null>(null)
  const timersRef = useRef<number[]>([])
  const formRef = useRef<HTMLElement>(null)

  const navState = location.state as
    | { prefillGenres?: string[]; hint?: string }
    | null

  useEffect(() => {
    return () => {
      timersRef.current.forEach((id) => window.clearTimeout(id))
    }
  }, [])

  useEffect(() => {
    if (navState?.hint) {
      setHint(navState.hint)
      window.requestAnimationFrame(() => {
        formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }
  }, [navState])

  function startFakeProgress() {
    timersRef.current.forEach((id) => window.clearTimeout(id))
    timersRef.current = []
    setStageIndex(0)
    PROGRESS_STAGES.forEach((_, i) => {
      if (i === 0) return
      const id = window.setTimeout(() => {
        setStageIndex(i)
      }, STAGE_INTERVAL_MS * i)
      timersRef.current.push(id)
    })
  }

  function stopFakeProgress() {
    timersRef.current.forEach((id) => window.clearTimeout(id))
    timersRef.current = []
  }

  function scrollToForm() {
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function handleSubmit(request: RecommendRequest) {
    setError(null)
    setLoading(true)
    startFakeProgress()

    const seen = loadSeen()
    const merged: RecommendRequest = {
      ...request,
      exclude_titles: [
        ...new Set([
          ...request.exclude_titles,
          ...seen.map((s) => s.title),
        ]),
      ],
      exclude_ids: [
        ...new Set([...request.exclude_ids, ...seen.map((s) => s.id)]),
      ],
    }

    try {
      const res = await postRecommend(merged)
      if (!res.success || !res.data) {
        throw new ApiError(res.message || '推荐失败')
      }

      setStageIndex(PROGRESS_STAGES.length - 1)
      saveSession({
        request: merged,
        result: res.data,
        message: res.message,
      })
      navigate('/result')
    } catch (err) {
      setError(err instanceof Error ? err.message : '推荐失败，请稍后重试')
    } finally {
      stopFakeProgress()
      setLoading(false)
    }
  }

  return (
    <div className="page page--home">
      <div className="hero-stage">
        <div className="hero-stage__atmosphere" aria-hidden="true">
          <div className="hero-stage__wash" />
          <div className="hero-stage__beam" />
          <div className="hero-stage__grain" />
          <div className="hero-stage__aperture" />
        </div>

        <SiteNav active="home" tone="over-hero" />

        <header className="hero">
          <h1 className="hero__brand-line">
            <span className="brand brand--hero">{BRAND_NAME}</span>
          </h1>
          <p className="hero__title">{BRAND_TAGLINE}</p>
          <div className="hero__cta">
            <button type="button" className="btn btn--primary" onClick={scrollToForm}>
              开始定片
            </button>
            <Link to="/browse" className="btn btn--ghost">
              逛片库
            </Link>
          </div>
        </header>
      </div>

      <main className="home-main" id="tonight" ref={formRef}>
        <div className="home-act">
          <header className="home-act__header">
            <p className="section-kicker">第二幕</p>
            <h2 className="home-act__title">定下今晚</h2>
            <p className="home-act__lead muted">
              说说心情与人群，其余可随手带过。
            </p>
          </header>

          {hint && <p className="hint-banner">{hint}</p>}
          <PreferenceForm
            onSubmit={(req) => void handleSubmit(req)}
            disabled={loading}
            initialGenres={navState?.prefillGenres}
          />
          {error && (
            <p className="error-banner" role="alert">
              {error}
            </p>
          )}
        </div>
      </main>

      <SiteFooter />
      <ProgressOverlay active={loading} stageIndex={stageIndex} />
    </div>
  )
}
