import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { ragQuery } from '@/api/rag'
import { notifyError } from '@/api/http'
import { useLibraryStore } from '@/stores/library'
import type { Language, RagSource } from '@/types'

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  sources?: RagSource[]
}

export const useChatStore = defineStore('chat', () => {
  const library = useLibraryStore()
  const turns = ref<ChatTurn[]>([])
  const loading = ref(false)
  const topK = ref(5)
  const language = ref<Language>('zh')
  const libraryCount = computed(() => library.saved.length)

  async function ask(question: string): Promise<void> {
    const q = question.trim()
    if (!q || loading.value) return
    if (!library.saved.length) {
      ElMessage.warning('请先在检索结果中收藏至少一篇文献')
      return
    }
    turns.value.push({ role: 'user', content: q })
    loading.value = true
    try {
      const out = await ragQuery({
        query: q,
        top_k: topK.value,
        language: language.value,
        documents: library.saved.slice(0, 100).map((article) => ({
          pmid: article.pmid,
          title: article.title,
          abstract: article.abstract.slice(0, 5000),
          journal: article.journal,
          publish_date: article.publish_date
        }))
      })
      turns.value.push({ role: 'assistant', content: out.answer, sources: out.sources })
    } catch (err) {
      notifyError(err)
      turns.value.push({ role: 'assistant', content: '请求失败，请确认收藏文献包含摘要并检查模型配置。' })
    } finally {
      loading.value = false
    }
  }

  function clear(): void {
    turns.value = []
  }

  return { turns, loading, topK, language, libraryCount, ask, clear }
})
