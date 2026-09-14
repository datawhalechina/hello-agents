<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { onMounted, ref } from 'vue'
import { api } from './api'

const route = useRoute()
const agentName = ref('Nova')
const llmReady = ref(true)

onMounted(async () => {
  try {
    const [info, health] = await Promise.all([
      api('/config/agent/info'),
      api('/health'),
    ])
    agentName.value = info.name || 'Nova'
    llmReady.value = !!health.llm_configured
  } catch {
    llmReady.value = false
  }
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="mark" />
        <div>
          <p class="eyebrow">Hello-Agents</p>
          <h1>{{ agentName }}</h1>
        </div>
      </div>
      <nav>
        <RouterLink to="/" :class="{ active: route.name === 'chat' }">对话</RouterLink>
        <RouterLink to="/sessions" :class="{ active: route.name === 'sessions' }">会话</RouterLink>
        <RouterLink to="/memory" :class="{ active: route.name === 'memory' }">记忆</RouterLink>
        <RouterLink to="/identity" :class="{ active: route.name === 'identity' }">身份</RouterLink>
        <RouterLink to="/reports" :class="{ active: route.name === 'reports' }">研报</RouterLink>
      </nav>
      <p class="sidebar-foot" :class="{ bad: !llmReady }">
        {{ llmReady ? 'LLM 已配置' : '未检测到 API Key' }}
      </p>
    </aside>
    <main class="stage">
      <RouterView />
    </main>
  </div>
</template>
