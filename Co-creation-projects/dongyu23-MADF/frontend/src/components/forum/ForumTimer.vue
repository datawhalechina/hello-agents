<template>
  <div 
    v-show="isVisible"
    class="forum-timer"
    :class="{ minimized: isMinimized, dragging: isDragging }"
    :style="style"
    @mousedown="startDrag"
    @touchstart="startDrag"
  >
    <!-- Maximized View -->
    <div v-if="!isMinimized" class="timer-content">
      <div class="timer-header">
        <span class="timer-title">剩余时间</span>
        <button class="minimize-btn" @click.stop="toggleMinimize">
          <minus-outlined />
        </button>
      </div>
      <div class="timer-display">
        {{ formattedTime }}
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- Minimized View -->
    <div v-else class="timer-minimized" @click.stop="handleClickMinimized">
      <div class="timer-circle">
        <clock-circle-outlined />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watchEffect } from 'vue'
import { MinusOutlined, ClockCircleOutlined } from '@ant-design/icons-vue'

const props = defineProps<{
  startTime: string
  durationMinutes: number
  status: string
}>()

const isMinimized = ref(true)
const isDragging = ref(false)
const position = ref({ x: window.innerWidth - 60, y: 100 }) // Default initial position
const remainingSeconds = ref(0)
const progress = ref(0)

const snapToEdge = () => {
  // Only snap horizontally
  const width = isMinimized.value ? 50 : 200
  const threshold = window.innerWidth / 2
  
  if (position.value.x + width / 2 > threshold) {
    // Snap to right
    position.value.x = window.innerWidth - width - 20 // 20px margin
  } else {
    // Snap to left
    position.value.x = 20
  }
}

// Dragging Logic
const offset = { x: 0, y: 0 }

const stopDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false
  
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('touchmove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
  window.removeEventListener('touchend', stopDrag)
  
  snapToEdge()
}

const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return
  
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  let newX = clientX - offset.x
  let newY = clientY - offset.y
  
  // Boundary constraints
  const maxX = window.innerWidth - (isMinimized.value ? 50 : 200)
  const maxY = window.innerHeight - (isMinimized.value ? 50 : 120)
  
  position.value.x = Math.max(0, Math.min(newX, maxX))
  position.value.y = Math.max(0, Math.min(newY, maxY))
}

const startDrag = (e: MouseEvent | TouchEvent) => {
  // Only allow drag on minimized state or header of maximized state?
  // Let's allow dragging anywhere for simplicity, but maybe restrict to minimized for better UX?
  // Actually, dragging the whole thing is fine.
  
  // Prevent drag if clicking minimize button
  if ((e.target as HTMLElement).closest('.minimize-btn')) return

  isDragging.value = true
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  
  offset.x = clientX - position.value.x
  offset.y = clientY - position.value.y
  
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('touchmove', onDrag)
  window.addEventListener('mouseup', stopDrag)
  window.addEventListener('touchend', stopDrag)
}

// Timer Logic

const updateTimer = () => {
  if (!props.startTime || props.status !== 'running') {
    remainingSeconds.value = 0
    progress.value = 0
    return
  }

  const start = new Date(props.startTime).getTime()
  const durationMs = props.durationMinutes * 60 * 1000
  const end = start + durationMs
  const now = Date.now()
  
  const remaining = Math.max(0, Math.floor((end - now) / 1000))
  remainingSeconds.value = remaining
  
  const totalSeconds = props.durationMinutes * 60
  progress.value = Math.min(100, Math.max(0, ((totalSeconds - remaining) / totalSeconds) * 100))
}

// Watch props to react to changes (especially start time update)
watchEffect(() => {
    if (props.status === 'running') {
        updateTimer()
    }
})

let timerInterval: number | null = null

onMounted(() => {
  updateTimer()
  timerInterval = window.setInterval(updateTimer, 1000)
  // Initial snap
  snapToEdge()
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})

const formattedTime = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60)
  const s = remainingSeconds.value % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
})

const style = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`
}))

const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
  // Re-snap after resize
  setTimeout(snapToEdge, 0)
}

const handleClickMinimized = () => {
    // If dragging happened, don't toggle
    // But we handle drag via separate listeners. 
    // click event fires after mouseup.
    // If we want to distinguish drag vs click, we can check displacement?
    // For simplicity, let's just toggle. 
    // But dragging might trigger click. 
    // Usually click is fine.
    if (!isDragging.value) {
        toggleMinimize()
    }
}
</script>

<style scoped>
.forum-timer {
  position: fixed;
  z-index: 1000;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  user-select: none;
  transition: width 0.3s, height 0.3s, border-radius 0.3s;
  /* Don't transition left/top during drag for smoothness */
}

.forum-timer:not(.dragging) {
  transition: left 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), top 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* Maximized State */
.timer-content {
  width: 200px;
  padding: 16px;
}

.timer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.timer-title {
  font-weight: 500;
  color: #666;
}

.minimize-btn {
  border: none;
  background: none;
  cursor: pointer;
  padding: 4px;
  color: #999;
}

.minimize-btn:hover {
  color: #1890ff;
}

.timer-display {
  font-size: 32px;
  font-weight: bold;
  color: #1890ff;
  text-align: center;
  font-family: monospace;
  margin-bottom: 8px;
}

.progress-bar {
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 1s linear;
}

/* Minimized State */
.timer-minimized {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #1890ff;
  color: white;
}

.timer-circle {
  font-size: 24px;
}

/* Hover effect for minimized */
.timer-minimized:hover {
  transform: scale(1.1);
}
</style>