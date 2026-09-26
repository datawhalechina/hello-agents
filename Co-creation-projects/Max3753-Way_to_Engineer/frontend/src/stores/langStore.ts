import { defineStore } from 'pinia'
import { ref } from 'vue'
import zh from '../locales/zh'
import en from '../locales/en'

type Lang = 'zh' | 'en'
type Messages = typeof zh

const STORAGE_KEY = 'lang'

const messages: Record<Lang, Messages> = { zh, en }

function getNestedValue(obj: Record<string, any>, path: string): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let current: any = obj
  for (const key of path.split('.')) {
    if (current == null) return path
    current = current[key]
  }
  return current ?? path
}

export const useLangStore = defineStore('lang', () => {
  const lang = ref<Lang>((localStorage.getItem(STORAGE_KEY) as Lang) || 'zh')

  function init() {
    const stored = localStorage.getItem(STORAGE_KEY) as Lang | null
    if (stored === 'zh' || stored === 'en') {
      lang.value = stored
    }
  }

  function toggleLang() {
    lang.value = lang.value === 'zh' ? 'en' : 'zh'
    localStorage.setItem(STORAGE_KEY, lang.value)
  }

  function t(key: string, params?: Record<string, string | number>): string {
    let value = getNestedValue(messages[lang.value] as Record<string, any>, key)
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        value = value.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      }
    }
    return value
  }

  return {
    lang,
    init,
    toggleLang,
    t,
  }
})
