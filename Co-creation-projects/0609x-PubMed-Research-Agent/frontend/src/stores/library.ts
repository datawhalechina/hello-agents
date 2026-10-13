// Personal literature library (favorites) persisted in localStorage.
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { Article, SavedArticle } from '@/types'

const STORAGE_KEY = 'pubmed-library'

function loadSaved(): SavedArticle[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as SavedArticle[]) : []
  } catch {
    return []
  }
}

function toSaved(article: Article): SavedArticle {
  return {
    pmid: article.pmid,
    title: article.title,
    abstract: article.abstract,
    doi: article.doi,
    authors: article.authors,
    journal: article.journal,
    publish_date: article.publish_date,
    publication_type: article.publication_type,
    impact_factor: article.impact_factor ?? null,
    saved_at: new Date().toISOString()
  }
}

export const useLibraryStore = defineStore('library', () => {
  const saved = ref<SavedArticle[]>(loadSaved())

  watch(
    saved,
    (list) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
      } catch {
        /* storage unavailable: keep in-memory state */
      }
    },
    { deep: true }
  )

  const count = computed(() => saved.value.length)

  function isSaved(pmid: string): boolean {
    return saved.value.some((item) => item.pmid === pmid)
  }

  function toggle(article: Article): void {
    if (isSaved(article.pmid)) {
      saved.value = saved.value.filter((item) => item.pmid !== article.pmid)
    } else {
      saved.value = [toSaved(article), ...saved.value]
    }
  }

  function remove(pmid: string): void {
    saved.value = saved.value.filter((item) => item.pmid !== pmid)
  }

  function clear(): void {
    saved.value = []
  }

  return { saved, count, isSaved, toggle, remove, clear }
})
