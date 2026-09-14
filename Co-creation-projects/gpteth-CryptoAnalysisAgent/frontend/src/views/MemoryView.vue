<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { renderMarkdown } from '../markdown'

const memories = ref([])
const longterm = ref('')
const selected = ref('longterm')

async function load() {
  const [daily, memory] = await Promise.all([
    api('/memory/list'),
    api('/memory/longterm'),
  ])
  memories.value = daily.memories || []
  longterm.value = memory.content || ''
}

onMounted(load)
</script>

<template>
  <div class="page memory-page">
    <header class="page-head">
      <h2>记忆系统</h2>
      <p>长期记忆 MEMORY.md，每日记忆自动按日期归档</p>
    </header>
    <div class="split">
      <div class="panel list">
        <div class="list-item" :class="{ active: selected === 'longterm' }" @click="selected = 'longterm'">
          <div>
            <strong>MEMORY.md</strong>
            <div class="muted">长期记忆</div>
          </div>
        </div>
        <div
          v-for="item in memories"
          :key="item.filename"
          class="list-item"
          :class="{ active: selected === item.filename }"
          @click="selected = item.filename"
        >
          <div>
            <strong>{{ item.date }}</strong>
            <div class="muted">{{ item.preview }}</div>
          </div>
        </div>
      </div>
      <article class="panel detail md">
        <div v-if="selected === 'longterm'" v-html="renderMarkdown(longterm)" />
        <div v-else-if="selected" v-html="renderMarkdown((memories.find(m => m.filename === selected) || {}).content || '')" />
        <div v-else class="empty">选择左侧一条记忆</div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.memory-page { min-height: 0; }
.split { flex: 1; display: flex; gap: 16px; min-height: 0; }
.list { width: 280px; overflow: auto; }
.detail { flex: 1; overflow: auto; padding: 20px; }
</style>
