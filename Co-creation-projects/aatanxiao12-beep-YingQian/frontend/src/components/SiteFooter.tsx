import { BRAND_NAME, BRAND_TAGLINE } from '../brand'

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <p className="site-footer__brand">{BRAND_NAME}</p>
      <p className="site-footer__tagline">{BRAND_TAGLINE}</p>
      <p>
        使用{' '}
        <a href="https://www.themoviedb.org/" target="_blank" rel="noreferrer">
          TMDB
        </a>{' '}
        API，但并非 TMDB 认证或赞助的产品。影片数据来自 The Movie Database。
      </p>
    </footer>
  )
}
