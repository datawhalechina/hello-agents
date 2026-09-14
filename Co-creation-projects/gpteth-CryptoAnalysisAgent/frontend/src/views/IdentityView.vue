<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const names = ['IDENTITY', 'SOUL', 'USER', 'MEMORY', 'AGENTS']
const labels = {
  IDENTITY: '身份',
  SOUL: '个性',
  USER: '用户',
  MEMORY: '长期记忆',
  AGENTS: '工作规则',
}
const selected = ref('IDENTITY')
const content = ref('')
const status = ref('')

async function load(name = selected.value) {
  selected.value = name
  const data = await api(`/config/${name}`)
  content.value = data.content || ''
  status.value = ''
}

async function save() {
  await api(`/config/${selected.value}`, {
    method: 'PUT',
    body: JSON.stringify({ content: content.value }),
  })
  status.value = '已保存，下一轮对话会读取最新身份配置'
}

async function resetAll() {
  await api('/config/reset?reset_sessions=false&reset_memory=false', { method: 'POST' })
  await load(selected.value)
  status.value = '已恢复模板'
}

onMounted(() => load('IDENTITY'))
</script>

<template>
  <div class="page identity-page">
    <header class="page-head">
      <h2>身份定制</h2>
      <p>通过 Markdown 配置文件自定义名称、个性和对用户的了解</p>
    </header>
    <div class="split">
      <div class="panel list">
        <div
          v-for="name in names"
          :key="name"
          class="list-item"
          :class="{ active: selected === name }"
          @click="load(name)"
        >
          <div>
            <strong>{{ name }}.md</strong>
            <div class="muted">{{ labels[name] }}</div>
          </div>
        </div>
      </div>
      <div class="editor-wrap">
        <textarea v-model="content" class="editor" />
        <div class="actions">
          <button class="primary" @click="save">保存</button>
          <button class="ghost" @click="resetAll">恢复模板</button>
          <span class="muted">{{ status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.identity-page { min-height: 0; }
.split { flex: 1; display: flex; gap: 16px; min-height: 0; }
.list { width: 240px; overflow: auto; }
.editor-wrap { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.editor {
  flex: 1;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  resize: none;
  outline: none;
  font-family: var(--mono);
  line-height: 1.6;
}
.actions { display: flex; gap: 10px; align-items: center; }
</style>
