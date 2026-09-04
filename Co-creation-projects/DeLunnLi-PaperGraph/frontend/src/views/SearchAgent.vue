<template>
  <div class="search-agent-page" :class="{ 'has-results': hasSearched, 'show-sidebar': showSidebar }">
    <div v-if="!hasSearched" class="centered-search">
      <div v-if="conversations.length > 0" class="initial-history-btn" @click="showSidebar = true">
        <MenuOutlined />
        <span>历史 ({{ conversations.length }})</span>
      </div>
      <div class="search-hero">
        <div class="logo-large">
          <RobotOutlined />
          <span>文献助手</span>
        </div>
        <div class="search-box">
          <a-textarea
            v-model:value="userInput"
            :rows="3"
            placeholder="输入关键词、研究方向或论文标题，即可检索相关论文"
            :disabled="isLoading"
            class="search-input"
            @compositionstart="onTextareaCompositionStart"
            @compositionend="onTextareaCompositionEnd"
            @keydown="handleKeydown"
          />
          <div class="search-actions">
            <a-button
              type="primary"
              size="large"
              :loading="isLoading"
              :disabled="!userInput.trim()"
              @click="sendMessage"
              class="send-btn"
            >
              <SendOutlined v-if="!isLoading" /> 搜索
            </a-button>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="chat-interface">
      <div class="chat-header">
        <div class="header-left">
          <a-button type="text" size="small" class="sidebar-toggle-btn" @click="showSidebar = !showSidebar">
            <MenuOutlined />
          </a-button>
          <RobotOutlined class="header-icon" />
          <span class="header-title">文献助手</span>
        </div>
        <div class="header-right">
          <a-space>
            <a-button size="small" @click="createNewConversation">
              <PlusOutlined /> 新对话
            </a-button>
          </a-space>
        </div>
      </div>
      <div class="messages-container" ref="messagesContainer">
        <div v-for="(msg, index) in messages" :key="index" class="message" :class="msg.role">
          <div v-if="msg.role === 'user'" class="user-bubble">
            <div class="message-content">{{ msg.content }}</div>
          </div>
          <div v-else class="ai-message">
            <div class="ai-avatar">
              <RobotOutlined />
            </div>
            <div class="ai-content">
              <div v-if="msg.content" class="ai-text" v-html="renderMarkdownWithLatex(msg.content)"></div>
              <SearchToolTrace v-if="msg.toolCalls?.length" :tool-calls="msg.toolCalls" />
              <div v-if="msg.searchParams" class="search-params">
                <a-tag v-if="msg.searchParams.venue" size="small" color="purple">{{ msg.searchParams.venue }}</a-tag>
              </div>
              <SearchResultPapers
                v-if="msg.results?.length"
                :papers="msg.results"
                :total="msg.total ?? msg.results.length"
                @save-one="saveOne"
                @save-all="saveAllFromMessage(msg)"
              />
              <div v-if="msg.results && msg.results.length === 0 && !isLoading && !msg.isError" class="no-results">
                <a-empty description="未找到相关论文" :image="Empty.PRESENTED_IMAGE_SIMPLE">
                  <template #description>
                    <span>未找到相关论文，请尝试调整搜索词</span>
                  </template>
                </a-empty>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="chat-input-area">
        <div class="input-wrapper">
          <a-textarea
            v-model:value="userInput"
            :rows="2"
            :disabled="isLoading"
            class="chat-textarea"
            @compositionstart="onTextareaCompositionStart"
            @compositionend="onTextareaCompositionEnd"
            @keydown="handleKeydown"
          />
          <a-button
            type="primary"
            class="chat-send-btn"
            :loading="isLoading"
            :disabled="!userInput.trim() || isLoading"
            @click="sendMessage"
          >
            <SendOutlined v-if="!isLoading" class="send-icon" />
          </a-button>
        </div>
        <div class="input-footer">
          <span class="hint">按 Enter 发送，Shift+Enter 换行</span>
        </div>
      </div>
      <div v-if="conversations.length > 0 && !showSidebar" class="sidebar-toggle right-toggle" @click="showSidebar = true">
        <MenuOutlined />
        <span>历史</span>
      </div>
    </div>
    <div v-if="conversations.length > 0" class="conversations-sidebar right-sidebar" :class="{ 'collapsed': !showSidebar }">
      <div class="sidebar-header">
        <span class="sidebar-title">历史对话</span>
        <a-button type="text" size="small" @click="showSidebar = false" class="close-sidebar-btn">
          <CloseOutlined />
        </a-button>
      </div>
      <div class="sidebar-content">
        <a-button type="dashed" block size="small" @click="createNewConversation" class="new-chat-btn-sidebar">
          <PlusOutlined /> 新对话
        </a-button>
        <div class="conversations-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: currentConversationId === conv.id }"
            @click="loadConversation(conv.id)"
          >
            <div class="conversation-title">{{ conv.title || '未命名对话' }}</div>
            <div class="conversation-meta">
              <span class="conversation-time">{{ formatTime(conv.timestamp) }}</span>
              <span class="conversation-count">{{ conv.messageCount }}条消息</span>
            </div>
            <a-button
              type="text"
              size="small"
              class="delete-btn"
              @click.stop="deleteConversation(conv.id)"
            >
              <DeleteOutlined />
            </a-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { message, Empty, Modal } from 'ant-design-vue'
import {
  RobotOutlined,
  SendOutlined,
  SaveOutlined,
  PlusOutlined,
  MenuOutlined,
  CloseOutlined,
  DeleteOutlined,
} from '@ant-design/icons-vue'
import SearchResultPapers from '@/components/search/SearchResultPapers.vue'
import SearchToolTrace from '@/components/search/SearchToolTrace.vue'
import { savePapers } from '@/services/api'
import type { Paper } from '@/types'
import { renderMarkdownWithLatex } from '@/utils/markdown'
import { useSearchConversations } from '@/composables/useSearchConversations'
import { useSearchAgentChat } from '@/composables/useSearchAgentChat'
defineOptions({ name: 'SearchAgent' })
interface ToolCall {
  name: string
  status: 'running' | 'success' | 'error'
  params?: Record<string, any>
  result_summary?: string
}
interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  searchParams?: any
  toolCalls?: ToolCall[]
  results?: Paper[]
  total?: number
  isError?: boolean
}
const messages = ref<Message[]>([])
const userInput = ref('')
const textareaImeComposing = ref(false)
const isLoading = ref(false)
const hasSearched = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const showSidebar = ref(false)
const route = useRoute()
function generateTitle(msgs: Message[]): string {
  const firstUserMsg = msgs.find(m => m.role === 'user')
  if (firstUserMsg) {
    const title = firstUserMsg.content.slice(0, 30)
    return title.length >= 30 ? title + '...' : title
  }
  return '未命名对话'
}
const {
  conversations,
  currentConversationId,
  ensureCurrentConversationId,
  persistConversationAndState,
  loadConversation,
  createNewConversation,
  removeConversation,
  initFromStorage,
  formatTime,
} = useSearchConversations<Message>({
  messages,
  hasSearched,
  userInput,
  showSidebar,
  titleFromMessages: generateTitle,
})
function deleteConversation(id: string) {
  Modal.confirm({
    title: '删除对话',
    content: '确定要删除这条对话记录吗？删除后无法恢复。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: () => {
      removeConversation(id)
      message.success('已删除对话')
    },
  })
}
onMounted(() => {
  initFromStorage()
  scrollToBottom()
})
onActivated(() => {
  scrollToBottom()
})
watch(
  () => String(route.name || '').toLowerCase(),
  (name) => {
    if (name === 'search') scrollToBottom()
  },
)
watch([hasSearched, currentConversationId], () => {
  if (hasSearched.value) {
    persistConversationAndState()
  }
})
function onTextareaCompositionStart() {
  textareaImeComposing.value = true
}
function onTextareaCompositionEnd() {
  textareaImeComposing.value = false
}
function handleKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey) return
  if (e.isComposing || textareaImeComposing.value) return
  e.preventDefault()
  sendMessage()
}
function scrollToBottom() {
  const apply = () => {
    const el = messagesContainer.value
    if (!el || !hasSearched.value) return
    el.scrollTop = el.scrollHeight
  }
  nextTick(() => {
    apply()
    requestAnimationFrame(() => {
      apply()
      requestAnimationFrame(apply)
    })
    window.setTimeout(apply, 60)
    window.setTimeout(apply, 220)
  })
}
const { sendMessage } = useSearchAgentChat({
  messages,
  userInput,
  isLoading,
  hasSearched,
  ensureCurrentConversationId,
  scrollToBottom,
  onConversationDirty: () => persistConversationAndState(),
})
const saveOne = async (paper: Paper) => {
  try {
    const res = await savePapers([paper])
    message.success(`已新增 ${res.added} 条到文献库`)
  } catch (e: unknown) {
    message.error((e as Error).message || '保存失败')
  }
}
const saveAllFromMessage = async (msg: Message) => {
  if (!msg.results || msg.results.length === 0) return
  try {
    const res = await savePapers(msg.results, { llm_classify: false })
    message.success(`已新增 ${res.added} 条到文献库`)
  } catch (e: unknown) {
    message.error((e as Error).message || '保存失败')
  }
}
watch(() => messages.value.length, scrollToBottom)
watch(currentConversationId, () => scrollToBottom())
</script>
<style scoped>
.search-agent-page {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: row;
  background: #f8fafc;
  overflow: hidden;
}
.search-agent-page.has-results {
  background: #fff;
}
.conversations-sidebar {
  width: 280px;
  min-width: 280px;
  background: #f1f5f9;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}
.conversations-sidebar.right-sidebar {
  position: fixed;
  right: 0;
  top: 64px;
  bottom: 0;
  z-index: 1000;
  border-right: none;
  border-left: 1px solid #e2e8f0;
  box-shadow: -2px 0 12px rgba(0,0,0,0.15);
}
.conversations-sidebar.collapsed {
  display: none;
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
}
.sidebar-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}
.close-sidebar-btn {
  color: #64748b;
}
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.new-chat-btn-sidebar {
  margin-bottom: 12px;
}
.conversations-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.conversation-item {
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}
.conversation-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59,130,246,0.1);
}
.conversation-item.active {
  border-color: #3b82f6;
  background: #eff6ff;
}
.conversation-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
  padding-right: 24px;
}
.conversation-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
}
.conversation-item .delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: #94a3b8;
}
.conversation-item:hover .delete-btn {
  opacity: 1;
}
.conversation-item .delete-btn:hover {
  color: #ef4444;
}
.sidebar-toggle {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: white;
  border: 1px solid #e2e8f0;
  border-left: none;
  border-radius: 0 8px 8px 0;
  padding: 8px 12px 8px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #64748b;
  z-index: 100;
  box-shadow: 2px 0 8px rgba(0,0,0,0.05);
}
.sidebar-toggle:hover {
  color: #3b82f6;
  border-color: #3b82f6;
}
.sidebar-toggle.right-toggle {
  left: auto;
  right: 0;
  top: 80px;
  transform: none;
  border-right: none;
  border-radius: 8px 0 0 8px;
  padding: 8px 8px 8px 12px;
  box-shadow: -2px 0 8px rgba(0,0,0,0.05);
  z-index: 200;
}
.search-agent-page.show-sidebar .sidebar-toggle.right-toggle {
  display: none;
}
.sidebar-toggle-btn {
  color: #64748b;
  padding: 4px 8px;
}
.centered-search {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: #f8fafc;
  overflow: hidden;
  z-index: 10;
}
.initial-history-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #64748b;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  transition: all 0.2s ease;
}
.initial-history-btn:hover {
  color: #3b82f6;
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59,130,246,0.15);
}
.search-hero {
  width: 100%;
  max-width: 720px;
  text-align: center;
}
.logo-large {
  font-size: 48px;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
}
.logo-large span {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.search-box {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border: 1px solid #e2e8f0;
  overflow: hidden;
  margin-bottom: 24px;
}
.search-input {
  border: none;
  resize: none;
  padding: 20px 24px;
  font-size: 15px;
  line-height: 1.6;
  background: transparent;
}
.search-input:focus {
  box-shadow: none;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid #f1f5f9;
  background: #fafafa;
}
.send-btn {
  height: 40px;
  padding: 0 24px;
  font-weight: 600;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  border: none;
}
.chat-interface {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
  overflow: hidden;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-icon {
  font-size: 22px;
  color: #3b82f6;
}
.header-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 16px;
}
.messages-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  padding: 20px 0;
  min-height: 0;
}
.message {
  display: flex;
  padding: 16px 20px;
  gap: 12px;
}
.message.user {
  justify-content: flex-end;
}
.user-bubble {
  max-width: 80%;
  background: #3b82f6;
  color: white;
  padding: 12px 16px;
  border-radius: 16px 16px 4px 16px;
  font-size: 15px;
  line-height: 1.5;
}
.ai-message {
  display: flex;
  gap: 12px;
  width: 100%;
}
.ai-avatar {
  width: 32px;
  height: 32px;
  background: #dbeafe;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  font-size: 18px;
  flex-shrink: 0;
}
.ai-content {
  flex: 1;
  min-width: 0;
  max-width: calc(100% - 50px);
}
.ai-text :deep(.katex) {
  font-size: 0.92em;
}
.ai-text {
  font-size: 15px;
  line-height: 1.7;
  color: #1e293b;
  margin-bottom: 12px;
}
.ai-text :deep(h4) {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin: 16px 0 8px;
  letter-spacing: 0.03em;
}
.ai-text :deep(h4:first-child) {
  margin-top: 4px;
}
.ai-text :deep(hr) {
  border: 0;
  border-top: 1px solid #e2e8f0;
  margin: 12px 0;
}
.ai-text :deep(ul) {
  margin: 6px 0 8px;
  padding-left: 1.1em;
}
.ai-text :deep(em) {
  color: #64748b;
  font-size: 13px;
}
.search-params {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.chat-input-area {
  padding: 16px 20px 24px;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.input-wrapper {
  display: flex;
  gap: 12px;
  background: #f8fafc;
  border-radius: 12px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
}
.chat-textarea {
  flex: 1;
  border: none;
  resize: none;
  background: transparent;
  padding: 4px;
  font-size: 15px;
}
.chat-textarea:focus {
  box-shadow: none;
}
.chat-send-btn {
  height: 36px;
  width: 36px;
  padding: 0;
  border-radius: 8px;
  background: #3b82f6;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.send-icon {
  font-size: 16px;
  line-height: 1;
}
.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
  margin-top: 8px;
}
.hint {
  font-size: 12px;
  color: #94a3b8;
}
.no-results {
  padding: 40px 0;
}
.messages-container::-webkit-scrollbar {
  width: 6px;
}
.messages-container::-webkit-scrollbar-track {
  background: transparent;
}
.messages-container::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
@media (max-width: 768px) {
  .search-hero {
  padding: 0 16px;
  }
  .logo-large {
  font-size: 36px;
  }
  .logo-large span {
  font-size: 24px;
  }
  .search-box {
  margin-bottom: 20px;
  }
  .search-actions {
  flex-direction: column;
  gap: 12px;
  }
  .send-btn {
  width: 100%;
  }
  .chat-interface {
  max-width: 100%;
  }
  .message {
  padding: 12px 16px;
  }
  .user-bubble {
  max-width: 90%;
  }
  .conversations-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 200;
  width: 280px;
  box-shadow: 2px 0 12px rgba(0,0,0,0.15);
  }
  .conversations-sidebar.right-sidebar {
  left: auto;
  right: 0;
  box-shadow: -2px 0 12px rgba(0,0,0,0.15);
  }
  .conversations-sidebar.collapsed {
  transform: translateX(-100%);
  display: flex;
  }
  .conversations-sidebar.right-sidebar.collapsed {
  transform: translateX(100%);
  }
  .current-conv-tag {
  max-width: 80px;
  }
  .sidebar-toggle.right-toggle {
  right: 0;
  left: auto;
  }
}
</style>