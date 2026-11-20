<template>
  <div class="chat-view">
    <el-card shadow="never" class="chat-card">
      <template #header>
        <div class="chat-head">
          <span class="chat-title">AI 收藏文献问答（{{ store.libraryCount }} 篇）</span>
          <div class="chat-options">
            <el-select v-model="store.language" size="small" style="width: 110px">
              <el-option value="zh" label="中文回答" />
              <el-option value="en" label="English" />
            </el-select>
            <el-select v-model="store.topK" size="small" style="width: 110px; margin-left: 12px">
              <el-option v-for="n in [3, 5, 8, 10]" :key="n" :value="n" :label="`Top ${n}`" />
            </el-select>
            <el-button size="small" text type="danger" @click="store.clear()">清空对话</el-button>
          </div>
        </div>
      </template>

      <div class="chat-body" ref="bodyRef">
        <el-empty
          v-if="!store.turns.length"
          :description="store.libraryCount ? '仅基于收藏文献提问，例如：这些研究采用了哪些实验方法？' : '收藏夹为空，请先在检索结果中收藏文献'"
          :image-size="90"
        />
        <div v-for="(turn, i) in store.turns" :key="i" :class="['turn', turn.role]">
          <div class="bubble">
            <div class="turn-label">{{ turn.role === 'user' ? '你' : 'AI' }}</div>
            <div class="turn-content" v-html="renderMarkdown(turn.content)" />
            <div v-if="turn.sources && turn.sources.length" class="sources">
              <el-tag
                v-for="s in turn.sources"
                :key="s.pmid"
                size="small"
                type="info"
                class="source-tag"
              >
                <el-link
                  type="primary"
                  :href="`https://pubmed.ncbi.nlm.nih.gov/${s.pmid}/`"
                  target="_blank"
                  rel="noopener"
                >PMID {{ s.pmid }}</el-link>
                <span class="source-score">{{ s.relevance_score.toFixed(3) }}</span>
              </el-tag>
            </div>
            <CopyButton v-if="turn.role === 'assistant'" :text="turn.content" />
          </div>
        </div>
        <div v-if="store.loading" class="turn assistant">
          <div class="bubble">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span style="margin-left: 8px">正在从收藏文献中检索证据并生成答案…</span>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="question"
          size="large"
          placeholder="输入你的问题…"
          clearable
          :disabled="!store.libraryCount"
          @keyup.enter="send"
        />
        <el-button type="primary" size="large" :loading="store.loading" :disabled="!store.libraryCount" @click="send">
          发送
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import CopyButton from '@/components/CopyButton.vue'
import { renderMarkdown } from '@/utils/format'

const store = useChatStore()
const question = ref('')
const bodyRef = ref<HTMLElement>()

async function send(): Promise<void> {
  const q = question.value
  if (!q.trim()) return
  await store.ask(q)
  question.value = ''
  await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
}
</script>

<style scoped>
.chat-card {
  height: calc(100vh - 130px);
  display: flex;
  flex-direction: column;
}
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.chat-title {
  font-weight: 600;
}
.chat-options {
  display: flex;
  align-items: center;
}
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  min-height: 260px;
}
.turn {
  margin-bottom: 16px;
}
.turn.user {
  text-align: right;
}
.turn.user .bubble {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  margin-left: 80px;
  text-align: left;
}
.turn.assistant .bubble {
  background: var(--el-fill-color-light);
  margin-right: 80px;
}
.bubble {
  display: inline-block;
  max-width: 100%;
  border-radius: 10px;
  padding: 12px 16px;
  text-align: left;
}
.turn-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.turn-content {
  line-height: 1.7;
}
.sources {
  margin-top: 8px;
}
.source-tag {
  margin-right: 6px;
}
.source-score {
  margin-left: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.chat-input {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
