import type { MovieDetail } from '../types'

const LANG_LABEL: Record<string, string> = {
  zh: '汉语',
  en: '英语',
  ja: '日语',
  ko: '韩语',
  fr: '法语',
  de: '德语',
  es: '西班牙语',
  it: '意大利语',
  hi: '印地语',
  th: '泰语',
}

export function languageLabel(code: string | null | undefined): string | null {
  if (!code) return null
  return LANG_LABEL[code] ?? code
}

/** 详情页信息块：导演 / 主演 / 国家等 */
export function DetailFacts({ detail }: { detail: MovieDetail }) {
  const lang = languageLabel(detail.original_language)
  const rows: { label: string; value: string }[] = []

  if (detail.directors.length) {
    rows.push({ label: '导演', value: detail.directors.join('、') })
  }
  if (detail.cast.length) {
    rows.push({ label: '主演', value: detail.cast.join('、') })
  }
  if (detail.countries.length) {
    rows.push({ label: '国家/地区', value: detail.countries.join('、') })
  }
  if (lang) {
    rows.push({ label: '语言', value: lang })
  }
  if (detail.original_title) {
    rows.push({ label: '原名', value: detail.original_title })
  }
  if (detail.vote_count != null && detail.vote_count > 0) {
    rows.push({ label: '评分人数', value: String(detail.vote_count) })
  }

  if (rows.length === 0) return null

  return (
    <dl className="detail-facts">
      {rows.map((row) => (
        <div key={row.label} className="detail-facts__row">
          <dt>{row.label}</dt>
          <dd>{row.value}</dd>
        </div>
      ))}
    </dl>
  )
}
