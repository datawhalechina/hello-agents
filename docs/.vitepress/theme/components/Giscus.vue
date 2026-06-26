<template>
  <div v-if="isChapterPage" class="giscus-wrapper">
    <div class="giscus-toggle" @click="toggleExpanded">
      <div class="giscus-toggle-title">
        <span class="giscus-toggle-label">{{ toggleLabel }}</span>
        <span class="giscus-toggle-hint">{{ toggleHint }}</span>
      </div>
      <span class="giscus-toggle-icon" :class="{ expanded }">▼</span>
    </div>
    <div class="giscus-content" :class="{ expanded }">
      <component :is="'script'"
        src="https://giscus.app/client.js"
        data-repo="datawhalechina/hello-agents"
        data-repo-id="R_kgDOPrUECg"
        data-category="💬 Exercises & Q&A"
        data-category-id="DIC_kwDOPrUECs4Cxfyu"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="top"
        :data-theme="giscusTheme"
        :data-lang="giscusLang"
        data-loading="lazy"
        crossorigin="anonymous"
        async
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useData, useRoute } from 'vitepress'

const { isDark } = useData()
const route = useRoute()

const expanded = ref(false)

// Determine if current page is a chapter page
const isChapterPage = computed(() => {
  const path = route.path.toLowerCase()
  return (
    path.includes('chapter') ||
    /[\u4e00-\u9fff]/.test(route.path) // contains Chinese characters (chapter pages)
  )
})

// Giscus theme follows site dark mode
const giscusTheme = computed(() => (isDark.value ? 'dark' : 'light'))

// Giscus language based on locale
const giscusLang = computed(() => {
  return route.path.startsWith('/en/') ? 'en' : 'zh-CN'
})

// Toggle labels
const toggleLabel = computed(() => {
  return route.path.startsWith('/en/')
    ? '💬 Discussion & Questions'
    : '💬 讨论与提问'
})

const toggleHint = computed(() => {
  return route.path.startsWith('/en/')
    ? 'Click to expand/collapse'
    : '点击展开/收起'
})

function toggleExpanded() {
  expanded.value = !expanded.value
}

// Sync Giscus theme when dark mode changes
// VitePress's default theme already handles this, but we ensure our component
// re-renders with the correct theme via the computed property
</script>

<style scoped>
.giscus-wrapper {
  margin-top: 60px;
  padding-top: 40px;
  border-top: 1px solid var(--vp-c-divider);
}

.giscus-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 15px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
  user-select: none;
}

.giscus-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.giscus-toggle-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.giscus-toggle-label {
  font-size: 1.1em;
  font-weight: 600;
  color: white;
}

.giscus-toggle-hint {
  font-size: 0.85em;
  color: rgba(255, 255, 255, 0.85);
}

.giscus-toggle-icon {
  font-size: 1em;
  transition: transform 0.3s ease;
  color: white;
}

.giscus-toggle-icon.expanded {
  transform: rotate(180deg);
}

.giscus-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.4s ease-out, opacity 0.3s ease;
  opacity: 0;
}

.giscus-content.expanded {
  max-height: 2000px;
  opacity: 1;
  transition: max-height 0.5s ease-in, opacity 0.4s ease;
}
</style>
