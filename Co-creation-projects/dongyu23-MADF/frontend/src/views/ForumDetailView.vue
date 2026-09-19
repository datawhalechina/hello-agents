<template>
  <div class="forum-detail-container">
    <div class="forum-header">
      <div class="header-left">
        <a-button @click="goBack" type="text">
          <arrow-left-outlined />
        </a-button>
        <span class="forum-topic">{{ forumStore.currentForum?.topic }}</span>
        <a-tag color="warning" v-if="forumStore.currentForum?.status === 'pending'">未开始</a-tag>
        <a-tag color="processing" v-if="forumStore.currentForum?.status === 'running'">进行中</a-tag>
        <a-tag color="default" v-if="forumStore.currentForum?.status === 'closed' || forumStore.currentForum?.status === 'finished'">已结束</a-tag>
      </div>
      <div class="header-right">
        <a-space>
            <a-button
                v-if="forumStore.currentForum?.status === 'pending'" 
                type="primary" 
                @click="handleStart"
                :loading="starting"
            >
                <play-circle-outlined /> 开始论坛
            </a-button>
            <a-popconfirm
              v-if="forumStore.currentForum?.status === 'running'"
              title="确定停止该论坛吗？"
              @confirm="handleStop"
            >
              <a-button danger>
                <pause-circle-outlined /> 停止论坛
              </a-button>
            </a-popconfirm>
            <a-button @click="showParticipantModal">
              <team-outlined /> 查看参与者
            </a-button>
            <a-popconfirm title="确定删除该论坛吗？" @confirm="handleDelete">
                <a-button danger>
                    <delete-outlined /> 删除
                </a-button>
            </a-popconfirm>
            <a-button @click="showSystemLogModal">
              <code-outlined /> 系统运行日志
            </a-button>
        </a-space>
      </div>
    </div>
    
    <MessageList 
      :messages="forumStore.messages" 
      :loading="forumStore.loading" 
    />
    
    <div class="chat-input-area" v-if="forumStore.currentForum?.status === 'running'">
      <div class="input-wrapper">
        <a-input-search
          v-model:value="userMessage"
          placeholder="作为观众发送消息..."
          enter-button="发送"
          size="large"
          @search="handleUserSend"
          :loading="sendingUserMessage"
        >
            <template #prefix>
                <user-outlined style="color: rgba(0,0,0,.25)" />
            </template>
        </a-input-search>
      </div>
    </div>
    
    <ForumTimer 
      v-if="forumStore.currentForum"
      :start-time="forumStore.currentForum.start_time || ''"
      :duration-minutes="forumStore.currentForum?.duration_minutes || 30" 
      :status="forumStore.currentForum?.status || 'pending'"
    />

    <!-- Participant Modal -->
    <a-modal
      v-model:open="isParticipantModalVisible"
      title="参与者列表"
      width="900px"
      :footer="null"
    >
      <div class="modal-content">
        <div class="modal-section">
          <ParticipantList />
        </div>
      </div>
    </a-modal>

    <!-- System Log Modal -->
    <a-modal
      v-model:open="isSystemLogModalVisible"
      title="系统运行日志"
      width="800px"
      :footer="null"
    >
      <div class="modal-content">
        <div class="modal-section">
          <SystemLogConsole />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { useForumWebSocket } from '@/composables/useForumWebSocket'
import MessageList from '@/components/forum/MessageList.vue'
import ForumTimer from '@/components/forum/ForumTimer.vue'
import ParticipantList from '@/components/forum/ParticipantList.vue'
import SystemLogConsole from '@/components/forum/SystemLogConsole.vue'
import { 
  ArrowLeftOutlined, 
  TeamOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined, 
  CodeOutlined, 
  UserOutlined, 
  PauseCircleOutlined
} from '@ant-design/icons-vue'

import { message } from 'ant-design-vue'
import request from '@/utils/request' // Import request

const route = useRoute()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const router = useRouter()

const starting = ref(false)
const sendingUserMessage = ref(false)
const userMessage = ref('')
const isParticipantModalVisible = ref(false)
const isSystemLogModalVisible = ref(false)
const forumId = Number(route.params.id)
const { connect, disconnect, isConnected } = useForumWebSocket(forumId)

const handleUserSend = async () => {
    if (!userMessage.value.trim()) return
    
    sendingUserMessage.value = true
    try {
        await request.post(`/forums/${forumId}/chat`, {
            content: userMessage.value,
            speaker: authStore.user?.username || '观众'
        })
        userMessage.value = ''
        message.success('发送成功')
    } catch (e) {
        message.error('发送失败')
    } finally {
        sendingUserMessage.value = false
    }
}

const showParticipantModal = () => {
  isParticipantModalVisible.value = true
}

const showSystemLogModal = () => {
  isSystemLogModalVisible.value = true
}

const goBack = () => {
    router.push('/forums')
}

onMounted(async () => {
  // Use a local flag to track if component is still mounted
  let isMounted = true
  
  // Cleanup function for this specific mount
  onUnmounted(() => {
    isMounted = false
    // We don't call disconnect() here as per requirements to keep connection alive
    // But we might want to save state
    forumStore.leaveForum()
  })
  
  try {
    // 1. Initial Load: Use store to fetch data (this handles cache internally)
    await forumStore.fetchForum(forumId)
    
    if (!isMounted) return

    // 2. Validate forum existence
    if (!forumStore.currentForum) {
         message.error('论坛不存在或加载失败')
         router.push('/forums')
         return
    }
    
    // 3. Background: Load participant info context (non-blocking)
    Promise.resolve(personaStore.fetchPersonas(authStore.user?.id)).catch(e => console.warn('Persona fetch failed', e))
    
    // 4. Background: Connect WS (non-blocking)
    // IMPORTANT: Check if WS is already connected for THIS forum
    // If not, connect. If yes, maybe just refresh messages?
    // connect() inside useForumWebSocket already handles idempotency
    try {
        await connect()
    } catch (e) {
        console.error('WS Connect error:', e)
    }

  } catch (e) {
    console.error('Failed to load forum details', e)
  } finally {
    if (isMounted) {
      forumStore.loading = false
    }
  }
})

// Remove the separate onUnmounted hook to avoid double cleanup/disconnect
// onUnmounted(() => {
//   disconnect()
// })

const handleDelete = async () => {
    try {
        await forumStore.deleteForum(forumId)
        message.success('论坛已删除')
        router.push('/forums')
    } catch (e: any) {
        // If 404, it's already deleted
        if (e.response && e.response.status === 404) {
             message.success('论坛已删除')
             router.push('/forums')
        } else {
             message.error('删除失败')
        }
    }
}

const handleStart = async () => {
    if (!forumStore.currentForum) return
    
    starting.value = true
    try {
        // Ensure WebSocket is connected BEFORE starting the forum task
        if (!isConnected.value) {
            await connect()
        }
        await forumStore.startForum(forumId)
        // fetchMessages is called by connect() on open, but good to ensure
        await forumStore.fetchMessages(forumId)
    } catch (e) {
        console.error('Start failed', e)
    } finally {
        starting.value = false
    }
}

const handleStop = async () => {
    if (!forumStore.currentForum) return
    try {
        await forumStore.stopForum(forumId)
    } catch (e) {
        console.error('Stop failed', e)
    }
}
</script>

<style scoped>
.forum-detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Occupy full viewport height */
  background: #fff;
  overflow: hidden;
}

.forum-header {
  height: 60px;
  flex-shrink: 0; /* Prevent shrinking */
  padding: 0 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  position: relative; /* Ensure stacking context */
  z-index: 100; /* Higher than content area */
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.forum-topic {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

.chat-input-area {
  padding: 12px 24px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.02);
}

.input-wrapper {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
