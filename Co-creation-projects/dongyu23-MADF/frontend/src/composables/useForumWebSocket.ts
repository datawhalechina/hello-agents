import { computed, onUnmounted } from 'vue'
import { useForumStore } from '@/stores/forum'

export function useForumWebSocket(forumId: number) {
  const store = useForumStore()

  // Use computed property to reflect the global connection status
  // We check if the global connection is for the CURRENT forum
  const isConnected = computed(() => {
    return store.isConnected && store.wsForumId === forumId
  })

  const connect = async () => {
    // Delegate to global store action
    store.connectWebSocket(forumId)
  }

  const disconnect = () => {
    // Ideally, we don't want to disconnect globally when component unmounts
    // if we want to keep the stream alive.
    // But if we want to explicitly stop, we can call store.disconnectWebSocket()
    // For now, we leave it empty or optional, as the store manages lifecycle.
    
    // However, if the user navigates away to a non-forum page, maybe we should disconnect?
    // The requirement says "页面退出不要终止 stream" (Do not terminate stream on page exit).
    // So we do NOTHING here.
  }

  // Remove onUnmounted hook that disconnects
  // onUnmounted(() => {
  //   disconnect()
  // })

  return {
    connect,
    disconnect,
    isConnected
  }
}
