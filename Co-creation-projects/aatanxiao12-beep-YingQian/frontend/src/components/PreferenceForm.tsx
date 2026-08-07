import { useEffect, useState, type FormEvent } from 'react'
import type {
  Mood,
  PartyType,
  RecommendRequest,
  RegionPreference,
  YearPreference,
} from '../types'
import {
  DEMO_REQUEST,
  GENRE_OPTIONS,
  MOODS,
  PARTY_TYPES,
  REGIONS,
  RUNTIME_OPTIONS,
  YEARS,
} from '../types'

interface PreferenceFormProps {
  onSubmit: (request: RecommendRequest) => void
  disabled?: boolean
  initialGenres?: string[]
}

const emptyForm = (): RecommendRequest => ({
  mood: '放松',
  party_type: '独自',
  genres: [],
  max_runtime_minutes: null,
  region_preference: '不限',
  year_preference: '不限',
  exclude_titles: [],
  spoilers_ok: false,
  free_text: '',
  exclude_ids: [],
})

export function PreferenceForm({
  onSubmit,
  disabled,
  initialGenres,
}: PreferenceFormProps) {
  const [form, setForm] = useState<RecommendRequest>(() => ({
    ...emptyForm(),
    genres: initialGenres?.length ? [...initialGenres] : [],
  }))
  const [excludeText, setExcludeText] = useState('')
  const [errors, setErrors] = useState<{ mood?: string; party_type?: string }>({})

  useEffect(() => {
    if (!initialGenres?.length) return
    setForm((prev) => ({
      ...prev,
      genres: [...new Set([...prev.genres, ...initialGenres])],
    }))
  }, [initialGenres])

  function fillDemo() {
    setForm({ ...DEMO_REQUEST })
    setExcludeText(DEMO_REQUEST.exclude_titles.join('、'))
    setErrors({})
  }

  function toggleGenre(genre: string) {
    setForm((prev) => {
      const has = prev.genres.includes(genre)
      return {
        ...prev,
        genres: has
          ? prev.genres.filter((g) => g !== genre)
          : [...prev.genres, genre],
      }
    })
  }

  function validate(): boolean {
    const next: { mood?: string; party_type?: string } = {}
    if (!form.mood) next.mood = '请选择心情'
    if (!form.party_type) next.party_type = '请选择观影人群'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!validate()) return

    const exclude_titles = excludeText
      .split(/[,，、\n]/)
      .map((s) => s.trim())
      .filter(Boolean)

    onSubmit({
      ...form,
      exclude_titles,
      exclude_ids: [],
    })
  }

  return (
    <form className="pref-form" onSubmit={handleSubmit} noValidate>
      <div className="pref-form__toolbar">
        <button
          type="button"
          className="btn btn--ghost btn--text"
          onClick={fillDemo}
          disabled={disabled}
        >
          填入示例
        </button>
      </div>

      <fieldset className="field-block" disabled={disabled}>
        <legend>
          此刻心情 <span className="req">*</span>
        </legend>
        <div className="choice-row" role="radiogroup" aria-label="心情">
          {MOODS.map((mood) => (
            <label key={mood} className="choice">
              <input
                type="radio"
                name="mood"
                value={mood}
                checked={form.mood === mood}
                onChange={() =>
                  setForm((p) => ({ ...p, mood: mood as Mood }))
                }
              />
              <span>{mood}</span>
            </label>
          ))}
        </div>
        {errors.mood && <p className="field-error">{errors.mood}</p>}
      </fieldset>

      <fieldset className="field-block" disabled={disabled}>
        <legend>
          观影人群 <span className="req">*</span>
        </legend>
        <div className="choice-row" role="radiogroup" aria-label="观影人群">
          {PARTY_TYPES.map((party) => (
            <label key={party} className="choice">
              <input
                type="radio"
                name="party_type"
                value={party}
                checked={form.party_type === party}
                onChange={() =>
                  setForm((p) => ({ ...p, party_type: party as PartyType }))
                }
              />
              <span>{party}</span>
            </label>
          ))}
        </div>
        {errors.party_type && (
          <p className="field-error">{errors.party_type}</p>
        )}
      </fieldset>

      <fieldset className="field-block" disabled={disabled}>
        <legend>偏好类型</legend>
        <div className="choice-row choice-row--wrap">
          {GENRE_OPTIONS.map((genre) => (
            <label key={genre} className="choice choice--check">
              <input
                type="checkbox"
                checked={form.genres.includes(genre)}
                onChange={() => toggleGenre(genre)}
              />
              <span>{genre}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="field-grid">
        <label className="field">
          <span>最长片长</span>
          <select
            value={form.max_runtime_minutes ?? ''}
            onChange={(e) => {
              const v = e.target.value
              setForm((p) => ({
                ...p,
                max_runtime_minutes: v === '' ? null : Number(v),
              }))
            }}
            disabled={disabled}
          >
            {RUNTIME_OPTIONS.map((opt) => (
              <option key={String(opt.value)} value={opt.value ?? ''}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>地区偏好</span>
          <select
            value={form.region_preference}
            onChange={(e) =>
              setForm((p) => ({
                ...p,
                region_preference: e.target.value as RegionPreference,
              }))
            }
            disabled={disabled}
          >
            {REGIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>年代偏好</span>
          <select
            value={form.year_preference}
            onChange={(e) =>
              setForm((p) => ({
                ...p,
                year_preference: e.target.value as YearPreference,
              }))
            }
            disabled={disabled}
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="field">
        <span>已看过（用顿号或逗号分隔）</span>
        <input
          type="text"
          value={excludeText}
          onChange={(e) => setExcludeText(e.target.value)}
          placeholder="例如：盗梦空间、星际穿越"
          disabled={disabled}
        />
      </label>

      <label className="field">
        <span>额外要求</span>
        <textarea
          rows={3}
          value={form.free_text}
          onChange={(e) =>
            setForm((p) => ({ ...p, free_text: e.target.value }))
          }
          placeholder="例如：节奏慢一点，适合睡前"
          disabled={disabled}
        />
      </label>

      <label className="field field--inline">
        <input
          type="checkbox"
          checked={form.spoilers_ok}
          onChange={(e) =>
            setForm((p) => ({ ...p, spoilers_ok: e.target.checked }))
          }
          disabled={disabled}
        />
        <span>允许简介含剧透</span>
      </label>

      <div className="pref-form__actions">
        <button type="submit" className="btn btn--primary" disabled={disabled}>
          {disabled ? '生成中…' : '生成片单'}
        </button>
      </div>
    </form>
  )
}
