<template>
  <div class="library-page">
    <a-layout class="library-layout">
      <a-layout-sider width="200" theme="light" class="library-sider">
        <div class="library-sider__title">文献库分类</div>
        <div v-if="storeRoot" class="library-sider__root">根目录：{{ storeRoot }}</div>
        <a-menu
          v-model:openKeys="openKeys"
          :selected-keys="[selectedKey]"
          mode="inline"
          @click="onCategoryClick"
        >
          <a-menu-item key="__all__">全部</a-menu-item>
          <template v-for="f in folders" :key="'row-' + f.category">
            <a-sub-menu v-if="f.children && f.children.length > 0" :key="'sub-' + f.category">
              <template #title>
                <span>{{ f.category }}</span>
                <span class="library-sider__count">（{{ f.count }}）</span>
              </template>
              <a-menu-item v-for="c in f.children" :key="c.category">
                <span class="library-sider__child-label">{{ c.label }}</span>
                <span class="library-sider__count">（{{ c.count }}）</span>
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item v-else :key="f.category">
              <span>{{ f.category }}</span>
              <span class="library-sider__count">（{{ f.count }}）</span>
            </a-menu-item>
          </template>
        </a-menu>
      </a-layout-sider>
      <a-layout-content class="library-content">
        <a-card :bordered="false" class="library-card">
          <template #title>
            <div class="library-card__title">
              <span class="library-card__title-text">我的文献库</span>
              <a-tag color="processing">{{ selectedCategoryLabel }}</a-tag>
            </div>
          </template>
          <template #extra>
            <a-space wrap>
              <a-tag color="blue">共 {{ pagination.total }} 篇</a-tag>
              <a-button :loading="loading" @click="load">刷新</a-button>
            </a-space>
          </template>
          <div class="library-toolbar">
            <a-input-search
              v-model:value="searchQuery"
              placeholder="搜索标题、作者、DOI…"
              allow-clear
              class="library-toolbar__search"
              @search="onSearchSubmit"
            />
          </div>
          <a-table
            class="library-table"
            :columns="columns"
            :data-source="papers"
            :loading="loading"
            :pagination="pagination"
            @change="onTableChange"
            :custom-row="customRow"
            :row-key="(r: Paper) => (r.id != null ? String(r.id) : `${r.title}-${r.doi || ''}`)"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <span class="lib-title-wrap">
                  <span class="lib-title-text">{{ record.title }}</span>
                  <a
                    v-if="record.source_url"
                    class="lib-title-ext"
                    :href="record.source_url"
                    target="_blank"
                    rel="noopener"
                    @click.stop
                  >原文 ↗</a>
                </span>
              </template>
              <template v-if="column.key === 'authors'">
                <span class="lib-authors-cell">{{ formatAuthorsEtAl(record.authors) }}</span>
              </template>
              <template v-if="column.key === 'year'">
                <span class="lib-year">{{ record.year ?? '—' }}</span>
              </template>
              <template v-if="column.key === 'category'">
                {{ record.category || '—' }}
              </template>
              <template v-if="column.key === 'journal_or_source'">
                <span v-if="record.journal && !String(record.journal).startsWith('arXiv:')" class="lib-venue">
                  <a-tag v-if="record.venue_type === 'conference'" color="purple" size="small" style="margin-right:4px">会议</a-tag>
                  <a-tag v-else-if="record.venue_type === 'journal'" color="cyan" size="small" style="margin-right:4px">期刊</a-tag>
                  {{ record.journal }}
                </span>
                <a-tag v-else>{{ record.source }}</a-tag>
              </template>
              <template v-if="column.key === 'actions'">
                <span class="lib-cell-actions" @click.stop>
                  <a-button type="link" size="small" @click="goReader(record)">阅读</a-button>
                  <a-button type="link" danger size="small" @click="onDelete(record)">删除</a-button>
                </span>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-layout-content>
    </a-layout>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { getLibrary, getLibraryCategoryFolders, deletePaper } from '@/services/api'
import type { LibraryCategoryFolder, Paper } from '@/types'
const router = useRouter()
const papers = ref<Paper[]>([])
const folders = ref<LibraryCategoryFolder[]>([])
const storeRoot = ref('')
const selectedKey = ref('__all__')
const openKeys = ref<string[]>([])
const loading = ref(false)
const searchQuery = ref('')
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
const selectedCategoryLabel = computed(() => {
  const sk = selectedKey.value
  if (sk === '__all__') return '全部分类'
  for (const f of folders.value) {
    if (f.category === sk) return f.category
    for (const c of f.children || []) {
      if (c.category === sk) return c.label || c.category
    }
  }
  return sk
})
const pagination = ref({
  total: 0,
  current: 1,
  pageSize: 10,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})
const columns = [
  { title: '标题', dataIndex: 'title', key: 'title', width: '28%', align: 'left' as const },
  { title: '作者', key: 'authors', width: '16%', align: 'left' as const },
  { title: '年份', key: 'year', width: '7%', align: 'center' as const },
  { title: '出版', key: 'journal_or_source', width: '14%', align: 'center' as const },
  { title: '领域', key: 'category', width: '24%', align: 'left' as const, ellipsis: true },
  { title: '操作', key: 'actions', width: '10%', align: 'center' as const },
]
function formatAuthorsEtAl(authors: Paper['authors'] | undefined): string {
  const names = (authors || []).map((a) => String(a?.name || '').trim()).filter(Boolean)
  if (names.length === 0) return '—'
  if (names.length <= 3) return names.join(', ')
  return `${names.slice(0, 3).join(', ')} et al.`
}
const loadFolders = async () => {
  try {
    const res = await getLibraryCategoryFolders()
    if (res.success) {
      folders.value = res.folders || []
      storeRoot.value = res.store_root || ''
      openKeys.value = folders.value
        .filter((f) => (f.children?.length ?? 0) > 0)
        .map((f) => `sub-${f.category}`)
    }
  } catch {
  }
}
let _loading = false
const load = async () => {
  if (_loading) return
  _loading = true
  loading.value = true
  try {
    const sk = selectedKey.value
    const cat = sk === '__all__' ? undefined : sk
    const q = searchQuery.value.trim() || undefined
    const ps = pagination.value.pageSize || 10
    const cur = pagination.value.current || 1
    const offset = (cur - 1) * ps
    const res = await getLibrary(ps, {
      offset,
      ...(cat ? { category: cat } : {}),
      ...(q ? { q } : {}),
    })
    if (res.success) {
      papers.value = res.papers ?? []
      pagination.value = { ...pagination.value, total: typeof res.total === 'number' ? res.total : papers.value.length }
    }
  } catch (e: unknown) {
    message.error((e as Error).message || '加载失败')
  } finally {
    loading.value = false
    _loading = false
  }
}
const onTableChange = (pag: { current?: number; pageSize?: number }) => {
  if (pag.current != null) pagination.value.current = pag.current
  if (pag.pageSize != null) pagination.value.pageSize = pag.pageSize
  void load()
}
const onCategoryClick = ({ key }: { key: string }) => {
  selectedKey.value = key
  pagination.value.current = 1
  void load()
}
const onSearchSubmit = () => {
  pagination.value.current = 1
  void load()
}
watch(searchQuery, () => {
  if (searchDebounceTimer != null) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    searchDebounceTimer = null
    pagination.value.current = 1
    void load()
  }, 420)
})
const openReaderUrl = (id: number) => {
  window.open(router.resolve({ path: `/library/read/${id}`, query: { standalone: '1' } }).href, '_blank', 'noopener,noreferrer')
}
const goReader = (record: Paper) => {
  if (record.id == null) { message.warning('无 ID，无法打开阅读页'); return }
  openReaderUrl(record.id)
}
const customRow = (record: Paper) => ({
  onClick: () => { if (record.id != null) openReaderUrl(record.id) },
  style: { cursor: record.id != null ? 'pointer' : 'default' },
})
const onDelete = (record: Paper) => {
  if (record.id == null) {
    message.warning('无 ID，无法删除')
    return
  }
  Modal.confirm({
    title: '确认删除该文献？',
    onOk: async () => {
      try {
        await deletePaper(record.id!)
        message.success('已删除')
        await loadFolders()
        await load()
      } catch (e: unknown) {
        message.error((e as Error).message || '删除失败')
      }
    },
  })
}
onMounted(async () => {
  await loadFolders()
  await load()
})
onBeforeUnmount(() => {
  if (searchDebounceTimer != null) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }
})
</script>
<style scoped>
.library-page {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
.library-card {
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.library-card :deep(.ant-card-head) {
  border-bottom: 1px solid rgba(5,5,5,0.06);
}
.library-card__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.library-card__title-text {
  font-size: 16px;
  font-weight: 600;
}
.library-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}
.library-toolbar__search {
  flex: 1 1 240px;
  max-width: 420px;
  min-width: 0;
}
.library-layout {
  background: transparent;
  gap: 16px;
  flex-direction: row;
  align-items: flex-start;
}
.library-sider {
  flex: 0 0 200px;
  max-width: 200px;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  height: fit-content;
  padding-top: 8px;
}
.library-sider__title {
  font-weight: 600;
  padding: 0 12px 8px;
  font-size: 14px;
}
.library-sider__root {
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  padding: 0 12px 8px;
  line-height: 1.4;
  word-break: break-all;
}
.library-sider__count {
  color: rgba(0,0,0,0.45);
  font-size: 12px;
}
.library-sider__child-label {
  word-break: break-all;
}
.library-sider :deep(.ant-menu-inline .ant-menu-item),
.library-sider :deep(.ant-menu-inline .ant-menu-submenu-title) {
  padding-inline: 12px !important;
}
.library-sider :deep(.ant-menu-submenu .ant-menu-item) {
  padding-inline: 24px !important;
}
.library-content {
  min-height: 360px;
  flex: 1;
  min-width: 0;
}
.library-table :deep(.ant-table-thead > tr > th) {
  font-weight: 600;
}
.library-table :deep(.ant-table-tbody > tr > td) {
  vertical-align: middle;
}
.lib-year {
  white-space: nowrap;
}
.lib-venue {
  font-size: 12px;
  color: #555;
  white-space: nowrap;
}
.library-table :deep(.ant-table-tbody > tr:hover > td) {
  background: #fafafa;
}
.lib-title-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  width: 100%;
  text-align: left;
  overflow-x: auto;
}
.lib-title-text {
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
}
.lib-title-ext {
  font-size: 12px;
  white-space: nowrap;
}
.lib-authors-cell {
  display: block;
  font-size: 13px;
  color: rgba(0,0,0,0.75);
  white-space: nowrap;
  overflow-x: auto;
  line-height: 1.45;
  word-break: break-word;
  text-align: left;
}
.lib-cell-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
}
@media (max-width: 900px) {
  .library-layout {
  flex-direction: column;
  }
  .library-sider {
  flex: 1 1 auto !important;
  max-width: none !important;
  width: 100% !important;
  }
  .library-toolbar__search {
  max-width: none;
  width: 100%;
  }
}
</style>