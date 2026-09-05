<template>
  <div class="gamification-panel">
    <div class="gp-header">
      <div class="gp-level-section">
        <div class="level-badge-circle">
          <span class="level-number">{{ profile.level }}</span>
          <span class="level-label">LV</span>
        </div>
        <div class="xp-info">
          <div class="xp-text">
            <span class="xp-amount">{{ profile.total_xp }} XP</span>
            <span class="xp-next">/ {{ nextLevelXp }} XP</span>
          </div>
          <div class="xp-bar">
            <div class="xp-fill" :style="{ width: xpPercent + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="gp-stats">
        <div class="stat-item" title="连续学习天数">
          <span class="stat-icon">🔥</span>
          <span class="stat-value">{{ profile.streak }}</span>
          <span class="stat-label">天</span>
        </div>
        <div class="stat-item" title="已获得徽章">
          <span class="stat-icon">🏅</span>
          <span class="stat-value">{{ profile.badges?.length || 0 }}</span>
          <span class="stat-label">徽章</span>
        </div>
      </div>
    </div>

    <div class="gp-badges">
      <div class="badges-title">
        <span>🏅 徽章墙</span>
        <span class="badges-count">{{ earnedCount }}/{{ allBadges.length }}</span>
      </div>
      <div class="badges-grid">
        <div
          v-for="badge in displayBadges"
          :key="badge.id"
          class="badge-item"
          :class="{ earned: isEarned(badge.id), locked: !isEarned(badge.id) }"
          :title="badge.description + (isEarned(badge.id) ? '' : ' (未获得)')"
        >
          <span class="badge-icon">{{ isEarned(badge.id) ? badge.icon : '🔒' }}</span>
          <span class="badge-name">{{ badge.name }}</span>
        </div>
      </div>
      <div v-if="allBadges.length > 7" class="badges-toggle" @click="showAllBadges = !showAllBadges">
        {{ showAllBadges ? '收起' : `查看全部 ${allBadges.length} 个徽章` }}
      </div>
    </div>

    <!-- XP获得通知 -->
    <transition name="xp-notify">
      <div v-if="xpNotification" class="xp-notification">
        <span class="xp-n-icon">✨</span>
        <span class="xp-n-text">+{{ xpNotification }} XP</span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'

interface Badge {
  id: string
  name: string
  description: string
  icon: string
  condition?: string
}

interface GamificationProfile {
  user_id: string
  total_xp: number
  level: number
  streak: number
  last_active_date: string
  badges: string[]
  xp_log: Array<{ amount: number; reason: string; timestamp: string }>
}

const XP_PER_LEVEL = 100

const props = withDefaults(defineProps<{
  userId?: string
}>(), {
  userId: '',
})

const emit = defineEmits<{
  (e: 'xp-earned', amount: number): void
}>()

const profile = ref<GamificationProfile>({
  user_id: '',
  total_xp: 0,
  level: 1,
  streak: 0,
  last_active_date: '',
  badges: [],
  xp_log: [],
})

const allBadges = ref<Badge[]>([])
const showAllBadges = ref(false)
const xpNotification = ref<number | null>(null)

const nextLevelXp = computed(() => profile.value.level * XP_PER_LEVEL)
const xpPercent = computed(() => {
  const currentLevelXp = (profile.value.level - 1) * XP_PER_LEVEL
  const progressInLevel = profile.value.total_xp - currentLevelXp
  return Math.min(100, (progressInLevel / XP_PER_LEVEL) * 100)
})

const earnedCount = computed(() => {
  return allBadges.value.filter(b => isEarned(b.id)).length
})

const displayBadges = computed(() => {
  if (showAllBadges.value || allBadges.value.length <= 7) return allBadges.value
  const earned = allBadges.value.filter(b => isEarned(b.id))
  const unearned = allBadges.value.filter(b => !isEarned(b.id))
  // Show all earned + enough unearned to fill 7
  const remaining = Math.max(0, 7 - earned.length)
  return [...earned, ...unearned.slice(0, remaining)]
})

function isEarned(badgeId: string): boolean {
  return profile.value.badges?.includes(badgeId) || false
}

async function loadProfile() {
  if (!props.userId) return
  try {
    const res = await axios.get('/api/gamification/profile', {
      params: { user_id: props.userId }
    })
    profile.value = res.data
  } catch (e) {
    console.error('加载游戏化数据失败', e)
  }
}

async function loadBadges() {
  try {
    const res = await axios.get('/api/gamification/badges')
    allBadges.value = res.data.badges
  } catch (e) {
    console.error('加载徽章数据失败', e)
  }
}

// 外部调用来显示XP通知
function showXpNotification(amount: number) {
  xpNotification.value = amount
  setTimeout(() => {
    xpNotification.value = null
  }, 2000)
  // Reload profile after notification
  setTimeout(() => loadProfile(), 500)
}

defineExpose({ showXpNotification, loadProfile })

onMounted(() => {
  loadProfile()
  loadBadges()
})
</script>

<style scoped>
.gamification-panel {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}

.gp-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.gp-level-section {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}

.level-badge-circle {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.level-number {
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}

.level-label {
  font-size: 9px;
  opacity: 0.85;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.xp-info {
  flex: 1;
  min-width: 120px;
}

.xp-text {
  font-size: 13px;
  margin-bottom: 4px;
}

.xp-amount {
  font-weight: 600;
  color: var(--color-text);
}

.xp-next {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.xp-bar {
  height: 8px;
  background: var(--color-bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.xp-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.gp-stats {
  display: flex;
  gap: 16px;
  flex-shrink: 0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  background: var(--color-bg-tertiary);
  padding: 4px 10px;
  border-radius: 8px;
  white-space: nowrap;
}

.stat-icon {
  font-size: 15px;
}

.stat-value {
  font-weight: 700;
  color: var(--color-text);
}

.stat-label {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.gp-badges {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.badges-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badges-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 400;
}

.badges-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  background: var(--color-bg-tertiary);
  transition: all 0.2s;
  cursor: default;
}

.badge-item.earned {
  opacity: 1;
}

.badge-item.locked {
  opacity: 0.5;
  filter: grayscale(1);
}

.badge-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.badge-icon {
  font-size: 16px;
}

.badge-name {
  font-weight: 500;
}

.badges-toggle {
  text-align: center;
  font-size: 12px;
  color: var(--color-primary);
  cursor: pointer;
  margin-top: 6px;
  padding: 2px 0;
}

.badges-toggle:hover {
  opacity: 0.8;
}

/* XP Notification */
.xp-notification {
  position: absolute;
  top: 50%;
  right: 20px;
  transform: translateY(-50%);
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  z-index: 10;
  pointer-events: none;
}

.xp-n-icon {
  font-size: 16px;
}

.xp-notify-enter-active {
  animation: xpPulse 0.3s ease-out;
}

.xp-notify-leave-active {
  animation: xpFade 0.4s ease-in;
}

@keyframes xpPulse {
  0% { transform: translateY(-50%) scale(0.5); opacity: 0; }
  60% { transform: translateY(-50%) scale(1.1); }
  100% { transform: translateY(-50%) scale(1); opacity: 1; }
}

@keyframes xpFade {
  0% { opacity: 1; transform: translateY(-50%) translateX(0); }
  100% { opacity: 0; transform: translateY(-50%) translateX(20px); }
}
</style>
