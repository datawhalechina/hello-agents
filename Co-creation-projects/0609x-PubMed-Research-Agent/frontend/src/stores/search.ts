import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { cancelSearchJob, createSearchJob, getHistory, getSearch, getSearchJob, openSearchJobEvents } from '@/api/search'
import { ApiError, notifyError } from '@/api/http'
import type { Language, SearchJob, SearchListItem, SearchMode, SearchOut, SortBy } from '@/types'

const TERMINAL_STATUSES = new Set(['completed', 'partial', 'failed', 'cancelled'])
const POLL_INTERVAL_MS = 1000

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

export const useSearchStore = defineStore('search', () => {
  const loading = ref(false)
  const query = ref('')
  const language = ref<Language>('en')
  const searchMode = ref<SearchMode>('advanced')
  const sortBy = ref<SortBy>('relevance')
  const minYear = ref<number | null>(null)
  const maxYear = ref<number | null>(null)
  const minImpactFactor = ref<number | null>(null)
  const maxResults = ref(10)
  const result = ref<SearchOut | null>(null)
  const job = ref<SearchJob | null>(null)
  const history = ref<SearchListItem[]>([])
  let pollToken = 0
  let stopActiveStream: (() => void) | null = null

  const progressPercent = computed(() => {
    if (!job.value) return 0
    return job.value.progress_percent
  })

  const jobStatusText = computed(() => {
    const labels: Record<string, string> = {
      queued: '任务已提交，正在等待处理',
      running: '正在检索文献并生成分析报告',
      completed: '分析完成',
      partial: '分析已完成，部分数据可能缺失',
      failed: '任务执行失败',
      cancelled: '任务已取消'
    }
    return job.value?.progress_message || labels[job.value?.status || ''] || '正在准备任务'
  })

  function waitForSse(jobId: string, token: number): Promise<SearchJob> {
    if (typeof EventSource === 'undefined') {
      return Promise.reject(new Error('EventSource is unavailable'))
    }
    return new Promise((resolve, reject) => {
      let settled = false
      let source: EventSource

      const cleanup = (): void => {
        source?.close()
        if (stopActiveStream === stop) stopActiveStream = null
      }
      const finish = (nextJob: SearchJob): void => {
        if (settled) return
        settled = true
        cleanup()
        resolve(nextJob)
      }
      const fail = (error: Error): void => {
        if (settled) return
        settled = true
        cleanup()
        reject(error)
      }
      const stop = (): void => fail(new Error('Progress stream cancelled'))
      stopActiveStream = stop
      source = openSearchJobEvents(
        jobId,
        (nextJob) => {
          if (token !== pollToken) {
            stop()
            return
          }
          job.value = nextJob
          if (TERMINAL_STATUSES.has(nextJob.status)) finish(nextJob)
        },
        fail
      )
    })
  }

  async function pollUntilTerminal(initialJob: SearchJob, token: number): Promise<SearchJob> {
    let currentJob = initialJob
    while (token === pollToken && !TERMINAL_STATUSES.has(currentJob.status)) {
      await delay(POLL_INTERVAL_MS)
      if (token !== pollToken) throw new Error('Progress polling cancelled')
      currentJob = await getSearchJob(currentJob.job_id)
      job.value = currentJob
    }
    return currentJob
  }

  async function run(): Promise<void> {
    const q = query.value.trim()
    if (!q || loading.value) return
    loading.value = true
    result.value = null
    job.value = null
    const currentToken = ++pollToken
    try {
      job.value = await createSearchJob({
        query: q,
        max_results: maxResults.value,
        language: language.value,
        search_mode: searchMode.value,
        sort_by: sortBy.value,
        min_year: minYear.value,
        max_year: maxYear.value,
        min_impact_factor: minImpactFactor.value
      })
      const initialJob = job.value
      try {
        job.value = await waitForSse(initialJob.job_id, currentToken)
      } catch {
        if (currentToken !== pollToken) return
        job.value = await pollUntilTerminal(job.value || initialJob, currentToken)
      }
      if (currentToken !== pollToken) return
      if (job.value.status === 'failed') {
        throw new ApiError(500, job.value.error_message || '检索任务执行失败')
      }
      if (job.value.status !== 'cancelled') {
        result.value = await getSearch(job.value.search_id)
      }
      await refreshHistory()
    } catch (err) {
      notifyError(err)
    } finally {
      loading.value = false
    }
  }

  async function cancel(): Promise<void> {
    const activeJob = job.value
    if (!activeJob || TERMINAL_STATUSES.has(activeJob.status)) return
    try {
      const cancelledJob = await cancelSearchJob(activeJob.job_id)
      ++pollToken
      stopActiveStream?.()
      job.value = cancelledJob
      await refreshHistory()
      loading.value = false
    } catch (err) {
      notifyError(err)
    }
  }

  async function refreshHistory(): Promise<void> {
    try {
      history.value = await getHistory(20)
    } catch (err) {
      notifyError(err)
    }
  }

  return {
    loading,
    query,
    language,
    searchMode,
    sortBy,
    minYear,
    maxYear,
    minImpactFactor,
    maxResults,
    result,
    job,
    history,
    progressPercent,
    jobStatusText,
    run,
    cancel,
    refreshHistory
  }
})
