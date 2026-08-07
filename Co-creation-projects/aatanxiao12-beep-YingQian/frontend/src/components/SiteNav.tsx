import { Link } from 'react-router-dom'
import { BRAND_NAME } from '../brand'

interface SiteNavProps {
  active?: 'home' | 'browse' | 'result'
  /** On the home hero, brand lives in the hero — keep nav quiet. */
  tone?: 'default' | 'over-hero'
}

export function SiteNav({ active, tone = 'default' }: SiteNavProps) {
  return (
    <nav
      className={
        tone === 'over-hero' ? 'site-nav site-nav--over-hero' : 'site-nav'
      }
      aria-label="主导航"
    >
      {tone === 'over-hero' ? (
        <span className="site-nav__spacer" aria-hidden="true" />
      ) : (
        <Link to="/" className="brand brand--link">
          {BRAND_NAME}
        </Link>
      )}
      <div className="site-nav__links">
        <Link
          to="/"
          className={active === 'home' ? 'site-nav__link is-active' : 'site-nav__link'}
        >
          荐片
        </Link>
        <Link
          to="/browse"
          className={active === 'browse' ? 'site-nav__link is-active' : 'site-nav__link'}
        >
          片库
        </Link>
      </div>
    </nav>
  )
}
