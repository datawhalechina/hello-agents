<template>
  <div class="chat-area" ref="chatAreaRef">
    <div v-if="loading && messages.length === 0" class="loading-state">
      <a-spin tip="加载消息记录..." />
    </div>
    
    <div v-else class="message-list">
      <ChatBubble
        v-for="msg in messages"
        :key="msg.id"
        :speaker-name="msg.speaker_name"
        :content="msg.content"
        :timestamp="msg.timestamp"
        :is-self="isSelf(msg)"
        :is-streaming="(msg as any).isStreaming"
        :moderator-id="msg.moderator_id"
        :thought="msg.thought"
      />
    </div>
    <div ref="bottomRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ChatBubble from './ChatBubble.vue'
import type { Message } from '@/stores/forum'
import { useAuthStore } from '@/stores/auth'
import { usePersonaStore } from '@/stores/persona'

const props = defineProps<{
  messages: Message[]
  loading: boolean
}>()

const authStore = useAuthStore()
const personaStore = usePersonaStore()
const bottomRef = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// Watch for both message count AND message content changes (streaming)
watch(() => props.messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

const isSelf = (msg: Message) => {
  if (msg.speaker_name === authStore.user?.username) return true
  if (msg.persona_id && personaStore.personas.find(p => p.id === msg.persona_id)) return true
  return false
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.chat-area {
  flex: 1;
  background: #f5f5f5;
  padding: 24px;
  overflow-y: auto;
  position: relative; /* Create stacking context for loading overlay */
  z-index: 1; /* Lower than header */
}

.loading-state {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(255, 255, 255, 0.8);
  z-index: 10;
}
</style>