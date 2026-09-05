<template>
  <div class="learning-view">
    <div class="view-header">
      <h1>{{ langStore.t('learning.title') }}</h1>
      <p>{{ langStore.t('learning.subtitle') }}</p>
    </div>

    <!-- 游戏化面板 -->
    <div class="gamification-wrapper">
      <GamificationPanel ref="gamificationRef" :userId="authStore.userId" />
    </div>
    
    <div class="paths-container">
      <div 
        v-for="path in paths" 
        :key="path.path"
        :class="['path-card', path.path, { selected: selectedPath === path.path }]"
        @click="selectPath(path.path)"
      >
        <div class="path-icon">{{ path.icon }}</div>
        <h3 class="path-title">{{ path.title }}</h3>
        <p class="path-desc">{{ path.description }}</p>
        <div class="path-stats">
          <span class="stat">
            <span class="stat-icon">📚</span>
            <span>{{ path.total_modules }} {{ langStore.t('learning.modules') }}</span>
          </span>
          <span class="stat">
            <span class="stat-icon">📝</span>
            <span>{{ path.total_lessons }} {{ langStore.t('learning.lessons') }}</span>
          </span>
        </div>
        <div v-if="selectedPath === path.path" class="selected-badge">{{ langStore.t('learning.selected') }}</div>
      </div>
    </div>
    
    <div v-if="selectedPath && pathDetail" class="path-detail">
      <!-- 水平检测状态卡片 -->
      <div v-if="assessmentResult" class="assessment-card">
        <div class="assessment-header">
          <div class="assessment-info">
            <span class="assessment-icon">📊</span>
            <div class="assessment-text">
              <h3>{{ langStore.t('learning.assessmentResult') }}</h3>
              <p class="assessment-level">
                {{ langStore.t('learning.currentLevel') }}<span :class="['level-badge', assessmentResult.level]">{{ getLevelText(assessmentResult.level) }}</span>
                <span class="assessment-score">{{ langStore.t('learning.score') }} {{ assessmentResult.score }} {{ langStore.t('learning.unit') }}</span>
              </p>
            </div>
          </div>
          <button class="btn btn-outline btn-sm" @click="retakeTest">
            🔄 {{ langStore.t('learning.retake') }}
          </button>
        </div>
        <div class="assessment-skills">
          <div 
            v-for="(score, skill) in assessmentResult.category_scores" 
            :key="skill"
            class="skill-item"
          >
            <span class="skill-name">{{ getCategoryName(skill) }}</span>
            <div class="skill-bar">
              <div class="skill-fill" :style="{ width: score + '%' }" :class="getScoreBarClass(score)"></div>
            </div>
            <span class="skill-score">{{ score }}%</span>
          </div>
        </div>
      </div>
      
      <div v-else class="assessment-prompt">
        <div class="prompt-content">
          <span class="prompt-icon">📝</span>
          <div class="prompt-text">
            <h3>{{ langStore.t('learning.assessmentPrompt') }}</h3>
            <p>{{ langStore.t('learning.assessmentPromptDesc') }}</p>
          </div>
          <button class="btn btn-primary" @click="startTest">
            {{ langStore.t('learning.startTest') }}
          </button>
        </div>
      </div>

      <div class="detail-header">
        <h2>{{ pathDetail.title }} - {{ langStore.t('learning.courseDetail') }}</h2>
        <div class="progress-summary">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: pathDetail.progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ pathDetail.progress.toFixed(0) }}{{ langStore.t('learning.completePercent') }}</span>
        </div>
      </div>
      
      <div class="modules-list">
        <div 
          v-for="module in pathDetail.modules" 
          :key="module.id"
          :class="['module-card', module.status]"
        >
          <div class="module-header">
            <span class="module-icon">{{ module.icon }}</span>
            <div class="module-info">
              <h3 class="module-title">{{ module.title }}</h3>
              <p class="module-desc">{{ module.description }}</p>
            </div>
            <div class="module-status">
              <span class="status-badge" :class="module.status">
                {{ getStatusText(module.status) }}
              </span>
            </div>
          </div>
          
          <div class="module-progress">
            <div class="progress-bar small">
              <div class="progress-fill" :style="{ width: module.progress + '%' }"></div>
            </div>
            <span class="progress-label">{{ module.progress.toFixed(0) }}%</span>
          </div>
          
          <div class="lessons-list">
            <div 
              v-for="lesson in module.lessons" 
              :key="lesson.id"
              :class="['lesson-item', { 
                completed: lesson.is_completed,
                clickable: module.status !== 'locked',
                locked: module.status === 'locked'
              }]"
              @click="openLesson(lesson, module)"
            >
              <span class="lesson-type-icon">{{ getLessonTypeIcon(lesson.type) }}</span>
              <div class="lesson-info">
                <span class="lesson-title">{{ lesson.title }}</span>
                <span class="lesson-meta">
                  <span class="lesson-duration">{{ lesson.duration_minutes }}{{ langStore.t('learning.minutes') }}</span>
                  <span class="lesson-type">{{ getLessonTypeText(lesson.type) }}</span>
                </span>
              </div>
              <span v-if="lesson.is_completed" class="completed-icon">✓</span>
              <span v-else-if="module.status === 'locked'" class="lock-icon">🔒</span>
              <span v-else class="arrow-icon">→</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 课程详情弹窗 -->
    <div v-if="selectedLesson" class="lesson-modal-overlay" @click.self="closeLesson">
      <div class="lesson-modal">
        <div class="modal-header">
          <span class="modal-icon">{{ getLessonTypeIcon(selectedLesson.type) }}</span>
          <div class="modal-title-area">
            <h3>{{ selectedLesson.title }}</h3>
            <span class="modal-module">{{ selectedModule?.title }}</span>
          </div>
          <button class="close-btn" @click="closeLesson">×</button>
        </div>
        
        <div class="modal-body">
          <p class="lesson-description">{{ selectedLesson.description }}</p>
          
          <div class="lesson-details">
            <div class="detail-item">
              <span class="detail-label">{{ langStore.t('learning.type') }}</span>
              <span class="detail-value">{{ getLessonTypeText(selectedLesson.type) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">{{ langStore.t('learning.duration') }}</span>
              <span class="detail-value">{{ selectedLesson.duration_minutes }} {{ langStore.t('learning.minutes') }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">{{ langStore.t('learning.status') }}</span>
              <span class="detail-value" :class="{ completed: selectedLesson.is_completed }">
                {{ selectedLesson.is_completed ? langStore.t('learning.completed') : langStore.t('learning.notCompleted') }}
              </span>
            </div>
          </div>
          
          <div class="lesson-content">
            <template v-if="selectedLesson && selectedLesson.content_markdown">
              <MarkdownRenderer :content="selectedLesson.content_markdown" />
            </template>
            <template v-else>
              <div class="no-content-prompt">
                <span class="no-content-icon">📚</span>
                <h4>在 Chat 中学习</h4>
                <p>点击"开始学习"进入对话模式，导师会为你讲解本课程内容</p>
              </div>
            </template>
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            v-if="!selectedLesson.is_completed" 
            class="btn btn-primary"
            @click="startLearning"
          >
            {{ langStore.t('learning.startLearning') }}
          </button>
          <button 
            v-if="!selectedLesson.is_completed" 
            class="btn btn-success"
            @click="completeLesson"
          >
            {{ langStore.t('learning.markComplete') }}
          </button>
          <button 
            v-else 
            class="btn btn-secondary"
            disabled
          >
            {{ langStore.t('learning.completed') }}
          </button>
          <button class="btn btn-outline" @click="closeLesson">{{ langStore.t('learning.close') }}</button>
        </div>
      </div>
    </div>
    
    <div v-if="coachData" class="coach-panel">
      <div class="coach-header">
        <span class="coach-icon">🎯</span>
        <h3>{{ langStore.t('learning.coachTitle') }}</h3>
      </div>
      <p class="coach-greeting">{{ coachData.greeting }}</p>
      <div class="coach-recommendations">
        <div 
          v-for="(rec, index) in coachData.recommendations" 
          :key="index"
          :class="['recommendation-item', { clickable: rec.type === 'next_lesson' || rec.type === 'select_path' }]"
          @click="handleRecClick(rec)"
        >
          <span class="rec-icon">{{ getRecIcon(rec.type) }}</span>
          <div class="rec-content">
            <span class="rec-title">{{ rec.title }}</span>
            <span class="rec-desc">{{ rec.description }}</span>
          </div>
          <span v-if="rec.type === 'next_lesson'" class="rec-arrow">→</span>
        </div>
      </div>
      <p class="coach-encouragement">{{ coachData.encouragement }}</p>
      
      <!-- 个性化学习计划 -->
      <div v-if="coachData.learning_plan" class="learning-plan-section">
        <div class="plan-header" @click="planExpanded = !planExpanded">
          <span class="plan-header-icon">📋</span>
          <span class="plan-header-title">个性化学习计划</span>
          <span class="plan-toggle">{{ planExpanded ? '收起' : '展开' }}</span>
        </div>
        <div v-if="planExpanded" class="plan-content">
          <div class="plan-markdown">{{ coachData.learning_plan }}</div>
        </div>
      </div>
    </div>

    <!-- 新徽章获得通知 -->
    <div v-if="newBadges.length > 0" class="badge-modal-overlay" @click.self="newBadges = []">
      <div class="badge-modal">
        <div class="badge-modal-header">
          <span class="badge-modal-icon">🎉</span>
          <h2>获得新徽章！</h2>
        </div>
        <div class="badge-modal-body">
          <div v-for="badge in newBadges" :key="badge.id" class="new-badge-item">
            <span class="new-badge-icon">{{ badge.icon }}</span>
            <div class="new-badge-info">
              <span class="new-badge-name">{{ badge.name }}</span>
              <span class="new-badge-desc">{{ badge.description }}</span>
            </div>
          </div>
        </div>
        <button class="btn btn-primary" @click="newBadges = []">太棒了！</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { useLangStore } from '../stores/langStore'
import { 
  getLevelText, getStatusText, 
  getLessonTypeIcon, getLessonTypeText, getRecIcon,
  getCategoryName, getScoreBarClass
} from '../utils/helpers'
import GamificationPanel from '../components/GamificationPanel.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const router = useRouter()
const authStore = useAuthStore()
const langStore = useLangStore()

// 游戏化相关
const gamificationRef = ref<InstanceType<typeof GamificationPanel> | null>(null)
const newBadges = ref<any[]>([])

// 学习计划折叠状态
const planExpanded = ref(false)

interface PathOverview {
  path: string
  title: string
  description: string
  icon: string
  total_modules: number
  total_lessons: number
}

interface Lesson {
  id: string
  title: string
  description: string
  type: string
  duration_minutes: number
  is_completed: boolean
  content_markdown?: string
}

interface Module {
  id: string
  title: string
  description: string
  icon: string
  order: number
  lessons: Lesson[]
  status: string
  progress: number
}

interface PathDetail {
  path: string
  title: string
  description: string
  icon: string
  modules: Module[]
  total_lessons: number
  completed_lessons: number
  progress: number
}

interface CoachRecommendation {
  type: string
  title: string
  description: string
  module_id?: string
  lesson_id?: string
  priority: number
}

interface CoachData {
  greeting: string
  recommendations: CoachRecommendation[]
  encouragement: string
  stats: Record<string, any>
  learning_plan?: string
}

const paths = ref<PathOverview[]>([])
const selectedPath = ref<string | null>(null)
const pathDetail = ref<PathDetail | null>(null)
const coachData = ref<CoachData | null>(null)
const assessmentResult = ref<any>(null)

// 课程弹窗状态
const selectedLesson = ref<Lesson | null>(null)
const selectedModule = ref<Module | null>(null)

onMounted(async () => {
  await loadPaths()
  
  // 从后端恢复上次选中的路径
  try {
    const progressRes = await axios.get('/api/learning/progress', {
      params: { user_id: authStore.userId }
    })
    if (progressRes.data.current_path) {
      selectedPath.value = progressRes.data.current_path
      await loadPathDetail(progressRes.data.current_path)
      await loadAssessmentResult(progressRes.data.current_path)
    }
  } catch (e) {
    console.error('Failed to restore selected path:', e)
  }
  
  await loadCoachData()
})

// keep-alive缓存恢复时刷新数据
onActivated(async () => {
  await loadCoachData()
  if (selectedPath.value) {
    await loadPathDetail(selectedPath.value)
    await loadAssessmentResult(selectedPath.value)
  }
})

const loadPaths = async () => {
  try {
    const response = await axios.get('/api/learning/paths', {
      params: { user_id: authStore.userId }
    })
    paths.value = response.data.paths
  } catch (error) {
    console.error('Failed to load paths:', error)
  }
}

let pathRequestSeq = 0

const selectPath = async (pathType: string) => {
  selectedPath.value = pathType
  const seq = ++pathRequestSeq
  
  // 持久化路径选择到后端
  try {
    await axios.post(`/api/learning/select-path/${pathType}`, null, {
      params: { user_id: authStore.userId }
    })
  } catch (e) {
    console.error('Failed to save path selection:', e)
  }
  
  if (seq !== pathRequestSeq) return
  await loadPathDetail(pathType)
  if (seq !== pathRequestSeq) return
  await loadAssessmentResult(pathType)
  if (seq !== pathRequestSeq) return
  await loadCoachData()
}

const loadPathDetail = async (pathType: string) => {
  try {
    const response = await axios.get(`/api/learning/paths/${pathType}`, {
      params: { user_id: authStore.userId }
    })
    pathDetail.value = response.data
  } catch (error) {
    console.error('Failed to load path detail:', error)
  }
}

const loadAssessmentResult = async (pathType: string) => {
  try {
    const response = await axios.get(`/api/assessment/check/${pathType}`, {
      params: { user_id: authStore.userId }
    })
    if (response.data.has_assessment && response.data.current_result) {
      assessmentResult.value = response.data.current_result
    } else {
      assessmentResult.value = null
    }
  } catch (error) {
    console.error('Failed to load assessment result:', error)
    assessmentResult.value = null
  }
}

const startTest = () => {
  console.log('startTest called, selectedPath:', selectedPath.value)
  if (!selectedPath.value) {
    console.error('No path selected')
    return
  }
  router.push({
    path: '/assessment',
    query: { path: selectedPath.value }
  })
}

const retakeTest = () => {
  if (confirm('重新测试将覆盖当前测试结果，确定要继续吗？')) {
    router.push({
      path: '/assessment',
      query: { path: selectedPath.value }
    })
  }
}

const loadCoachData = async () => {
  try {
    const response = await axios.get('/api/learning/coach', {
      params: { user_id: authStore.userId }
    })
    coachData.value = response.data
  } catch (error) {
    console.error('Failed to load coach data:', error)
  }
}

const handleRecClick = (rec: CoachRecommendation) => {
  if (rec.type === 'select_path') {
    // 滚动到路径选择区域
    const el = document.querySelector('.paths-container')
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  
  if ((rec.type === 'next_lesson' || rec.type === 'review') && rec.lesson_id && rec.module_id && pathDetail.value) {
    // 查找对应模块
    const mod = pathDetail.value.modules.find(m => m.id === rec.module_id)
    if (!mod) return
    
    // 查找对应课程
    const lesson = mod.lessons.find(l => l.id === rec.lesson_id)
    if (!lesson) return
    
    // 检查是否锁定
    if (mod.status === 'locked') return
    
    // 打开课程详情弹窗
    selectedLesson.value = lesson
    selectedModule.value = mod
  }
}

const openLesson = (lesson: Lesson, module: Module) => {
  if (module.status === 'locked') {
    return // 锁定的模块不能打开
  }
  selectedLesson.value = lesson
  selectedModule.value = module
}

const closeLesson = () => {
  selectedLesson.value = null
  selectedModule.value = null
}

const startLearning = async () => {
  if (!selectedLesson.value || !selectedModule.value || !selectedPath.value) return
  
  // 检查是否已测试
  try {
    const checkResponse = await axios.get(`/api/assessment/check/${selectedPath.value}`, {
      params: { user_id: authStore.userId }
    })
    const { has_assessment, current_result } = checkResponse.data
    
    if (!has_assessment) {
      // 未测试过，跳转到测试页面
      router.push({
        path: '/assessment',
        query: { path: selectedPath.value }
      })
      return
    }
    
    // 已测试过，构建学习消息（包含水平信息）
    const lesson = selectedLesson.value
    const module = selectedModule.value
    let message = `我想学习"${lesson.title}"这个课程。这是"${module.title}"模块中的内容，类型是${getLessonTypeText(lesson.type)}。请帮我讲解这个主题。`
    
    // 如果有测试结果，添加到消息中
    if (current_result) {
      message = `我已经完成了水平检测，得分${current_result.score}分，水平为${getLevelText(current_result.level)}。\n\n${message}`
    }
    
    // 存储到sessionStorage，Chat页面会读取
    const context = {
      message: message,
      path_type: selectedPath.value,
      user_level: current_result?.level || null,
      skill_levels: current_result?.category_scores || null,
      lesson_id: lesson.id,
      module_id: module.id,
      lesson_title: lesson.title,
      module_title: module.title
    }
    sessionStorage.setItem('pendingLearningContext', JSON.stringify(context))
    
    // 跳转到聊天页面
    router.push('/')
  } catch (error) {
    console.error('Failed to check assessment:', error)
    // 出错时直接跳转到测试
    router.push({
      path: '/assessment',
      query: { path: selectedPath.value }
    })
  }
}

const completeLesson = async () => {
  if (!selectedLesson.value || !selectedPath.value) return
  
  try {
    const response = await axios.post(`/api/learning/complete-lesson/${selectedLesson.value.id}`, null, {
      params: { user_id: authStore.userId }
    })
    selectedLesson.value.is_completed = true
    
    // 处理XP奖励
    const xp = response.data.xp_awarded
    if (xp > 0) {
      gamificationRef.value?.showXpNotification(xp)
    }
    
    // 处理新徽章
    const badges = response.data.new_badges
    if (badges && badges.length > 0) {
      newBadges.value = badges
    }
    
    // 重新加载路径详情以更新进度
    await loadPathDetail(selectedPath.value)
    await loadCoachData()
  } catch (error) {
    console.error('Failed to complete lesson:', error)
  }
}
</script>

<style scoped>
.learning-view {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: #f8f9fa;
  overflow-y: auto;
}

.view-header {
  padding: 24px 32px;
  background: white;
  border-bottom: 1px solid #e5e5e5;
}

.view-header h1 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #1a1a1a;
}

.view-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.paths-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 24px 32px;
}

.path-card {
  position: relative;
  background: white;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.path-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.path-card.selected {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.path-card.frontend { border-top: 4px solid #764ba2; }
.path-card.backend { border-top: 4px solid #f5222d; }
.path-card.fullstack { border-top: 4px solid #52c41a; }

.path-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.path-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #1a1a1a;
}

.path-desc {
  margin: 0 0 16px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.path-stats {
  display: flex;
  gap: 16px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #999;
}

.stat-icon {
  font-size: 14px;
}

.selected-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  background: #667eea;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.path-detail {
  padding: 0 32px 24px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.detail-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1a1a1a;
}

.progress-summary {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar.small {
  width: 100px;
  height: 6px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.modules-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.module-card.locked {
  opacity: 0.7;
  background: #fafafa;
}

.module-card.completed {
  border-left: 4px solid #52c41a;
}

.module-card.in_progress {
  border-left: 4px solid #667eea;
}

.module-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.module-icon {
  font-size: 32px;
}

.module-info {
  flex: 1;
}

.module-title {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #1a1a1a;
}

.module-desc {
  margin: 0;
  font-size: 13px;
  color: #666;
}

.module-status {
  flex-shrink: 0;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.not_started { background: #f5f5f5; color: #999; }
.status-badge.in_progress { background: #e6f7ff; color: #1890ff; }
.status-badge.completed { background: #f6ffed; color: #52c41a; }
.status-badge.locked { background: #f5f5f5; color: #999; }

.module-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.progress-label {
  font-size: 12px;
  color: #999;
}

.lessons-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lesson-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.2s;
}

.lesson-item.clickable {
  cursor: pointer;
}

.lesson-item.clickable:hover {
  background: #e8e8e8;
  transform: translateX(4px);
}

.lesson-item.locked {
  cursor: not-allowed;
  opacity: 0.6;
}

.lesson-item.completed {
  background: #f6ffed;
}

.lesson-type-icon {
  font-size: 18px;
}

.lesson-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.lesson-title {
  font-size: 14px;
  color: #1a1a1a;
  font-weight: 500;
}

.lesson-meta {
  display: flex;
  gap: 12px;
  margin-top: 2px;
}

.lesson-duration, .lesson-type {
  font-size: 12px;
  color: #999;
}

.completed-icon {
  color: #52c41a;
  font-weight: 600;
  font-size: 16px;
}

.lock-icon {
  color: #999;
  font-size: 14px;
}

.arrow-icon {
  color: #667eea;
  font-size: 16px;
  opacity: 0;
  transition: opacity 0.2s;
}

.lesson-item.clickable:hover .arrow-icon {
  opacity: 1;
}

/* 弹窗样式 */
.lesson-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.lesson-modal {
  background: white;
  border-radius: 16px;
  width: 95%;
  max-width: 820px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8e8;
}

.modal-icon {
  font-size: 36px;
}

.modal-title-area {
  flex: 1;
}

.modal-title-area h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  color: #1a1a1a;
}

.modal-module {
  font-size: 13px;
  color: #999;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f5f5f5;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: #e8e8e8;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.lesson-description {
  font-size: 15px;
  color: #333;
  line-height: 1.6;
  margin: 0 0 20px 0;
}

.lesson-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: #999;
}

.detail-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.detail-value.completed {
  color: #52c41a;
}

.lesson-content h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #1a1a1a;
}

.lesson-content p {
  margin: 0 0 16px 0;
  color: #666;
  line-height: 1.6;
}

.lesson-content :deep(.markdown-renderer) {
  font-size: 14px;
  line-height: 1.8;
}

.lesson-content :deep(.markdown-body) h1,
.lesson-content :deep(.markdown-body) h2,
.lesson-content :deep(.markdown-body) h3 {
  margin-top: 24px;
  margin-bottom: 12px;
}

.lesson-content :deep(.markdown-body) h2 {
  font-size: 20px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.lesson-content :deep(.markdown-body) h3 {
  font-size: 16px;
}

.lesson-content :deep(.markdown-body) p {
  margin: 0 0 12px 0;
  color: #333;
  line-height: 1.8;
}

.lesson-content :deep(.markdown-body) code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}

.lesson-content :deep(.markdown-body) pre {
  margin: 12px 0 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.lesson-content :deep(.markdown-body) table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0 16px;
  font-size: 13px;
}

.lesson-content :deep(.markdown-body) th,
.lesson-content :deep(.markdown-body) td {
  border: 1px solid #e0e0e0;
  padding: 8px 12px;
  text-align: left;
}

.lesson-content :deep(.markdown-body) th {
  background: #f8f9fa;
  font-weight: 600;
}

.lesson-content :deep(.markdown-body) blockquote {
  margin: 12px 0;
  padding: 10px 16px;
  background: #f0f5ff;
  border-left: 4px solid #667eea;
  border-radius: 0 8px 8px 0;
  color: #555;
}

.lesson-content :deep(.markdown-body) blockquote p {
  margin: 0;
  color: #555;
}

.lesson-content :deep(.markdown-body) ul,
.lesson-content :deep(.markdown-body) ol {
  padding-left: 24px;
  margin: 8px 0 12px;
}

.lesson-content :deep(.markdown-body) li {
  margin: 4px 0;
}

/* 无内容时的提示 */
.no-content-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.no-content-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.no-content-prompt h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.no-content-prompt p {
  margin: 0;
  color: #999;
  font-size: 14px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e8e8e8;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-success {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.btn-success:hover {
  background: #f6ffed;
  border-color: #52c41a;
}

.btn-secondary {
  background: #f6ffed;
  color: #52c41a;
  cursor: not-allowed;
}

.btn-outline {
  background: white;
  border: 1px solid #d9d9d9;
  color: #666;
}

.btn-outline:hover {
  border-color: #667eea;
  color: #667eea;
}

/* 教练面板 */
.coach-panel {
  margin: 0 32px 24px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.coach-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.coach-icon {
  font-size: 24px;
}

.coach-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1a1a1a;
}

.coach-greeting {
  margin: 0 0 16px 0;
  color: #666;
  font-size: 14px;
}

.coach-recommendations {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.recommendation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.rec-icon {
  font-size: 20px;
}

.rec-content {
  display: flex;
  flex-direction: column;
}

.rec-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}

.rec-desc {
  font-size: 12px;
  color: #999;
}

.recommendation-item.clickable {
  cursor: pointer;
  transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}

.recommendation-item.clickable:hover {
  background: #eef0f5;
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.recommendation-item.clickable:active {
  transform: translateX(1px);
}

.rec-arrow {
  font-size: 14px;
  color: #667eea;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.15s, transform 0.15s;
  flex-shrink: 0;
}

.recommendation-item.clickable:hover .rec-arrow {
  opacity: 1;
  transform: translateX(2px);
}

@media (prefers-color-scheme: dark) {
  .recommendation-item.clickable:hover {
    background: #2a2a2a;
  }
}

.coach-encouragement {
  margin: 0;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 8px;
  font-size: 14px;
  color: #667eea;
  font-weight: 500;
  text-align: center;
}

/* 学习计划卡片 */
.learning-plan-section {
  margin-top: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  overflow: hidden;
  background: white;
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  background: #fafafa;
  transition: background 0.15s;
  user-select: none;
}

.plan-header:hover {
  background: #f0f0f0;
}

.plan-header-icon {
  font-size: 16px;
}

.plan-header-title {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.plan-toggle {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
}

.plan-content {
  border-top: 1px solid #e8e8e8;
  max-height: 60vh;
  overflow-y: auto;
}

.plan-markdown {
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

@media (prefers-color-scheme: dark) {
  .learning-plan-section {
    border-color: #333;
    background: #1e1e1e;
  }
  .plan-header {
    background: #252525;
  }
  .plan-header:hover {
    background: #2a2a2a;
  }
  .plan-header-title {
    color: #ccc;
  }
  .plan-markdown {
    color: #ccc;
  }
  .plan-content {
    border-color: #333;
  }
}

/* 水平检测卡片 */
.assessment-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.assessment-card .assessment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.assessment-card .assessment-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assessment-card .assessment-icon {
  font-size: 32px;
}

.assessment-card .assessment-text h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #1a1a1a;
}

.assessment-card .assessment-level {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.assessment-card .assessment-score {
  margin-left: 12px;
  color: #999;
}

.level-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 13px;
}

.level-badge.beginner { background: #f6ffed; color: #52c41a; }
.level-badge.intermediate { background: #e6f7ff; color: #1890ff; }
.level-badge.advanced { background: #fff2f0; color: #ff4d4f; }

.assessment-card .assessment-skills {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.assessment-card .skill-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.assessment-card .skill-name {
  font-size: 13px;
  color: #666;
  width: 80px;
  flex-shrink: 0;
}

.assessment-card .skill-bar {
  flex: 1;
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.assessment-card .skill-fill {
  height: 100%;
  border-radius: 3px;
}

.assessment-card .skill-fill.excellent { background: #52c41a; }
.assessment-card .skill-fill.good { background: #1890ff; }
.assessment-card .skill-fill.fair { background: #fa8c16; }
.assessment-card .skill-fill.poor { background: #ff4d4f; }

.assessment-card .skill-score {
  font-size: 13px;
  color: #999;
  width: 40px;
  text-align: right;
}

/* 测试提示卡片 */
.assessment-prompt {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.assessment-prompt .prompt-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.assessment-prompt .prompt-icon {
  font-size: 40px;
}

.assessment-prompt .prompt-text {
  flex: 1;
}

.assessment-prompt .prompt-text h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: white;
}

.assessment-prompt .prompt-text p {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.assessment-prompt .btn-primary {
  background: white;
  color: #667eea;
}

.assessment-prompt .btn-primary:hover {
  background: #f5f5f5;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

/* 游戏化面板包裹 */
.gamification-wrapper {
  padding: 0 32px;
  margin-top: 16px;
}

/* 徽章通知弹窗 */
.badge-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.badge-modal {
  background: var(--color-bg-secondary, #fff);
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s ease;
}

.badge-modal-header {
  margin-bottom: 20px;
}

.badge-modal-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 8px;
}

.badge-modal-header h2 {
  margin: 0;
  font-size: 22px;
  color: var(--color-text, #1a1a1a);
}

.badge-modal-body {
  margin-bottom: 24px;
}

.new-badge-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  background: var(--color-bg-tertiary, #f5f5f5);
  border-radius: 12px;
  margin-bottom: 8px;
}

.new-badge-icon {
  font-size: 36px;
}

.new-badge-info {
  text-align: left;
}

.new-badge-name {
  display: block;
  font-weight: 700;
  font-size: 16px;
  color: var(--color-text, #1a1a1a);
}

.new-badge-desc {
  display: block;
  font-size: 13px;
  color: var(--color-text-secondary, #666);
  margin-top: 2px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@media (prefers-color-scheme: dark) {
  .lesson-modal {
    background: #1e1e1e;
  }
  .modal-header {
    border-color: #333;
  }
  .modal-title-area h3 {
    color: #e0e0e0;
  }
  .lesson-description {
    color: #ccc;
  }
  .detail-value {
    color: #ddd;
  }
  .lesson-content :deep(.markdown-body) p,
  .lesson-content :deep(.markdown-body) li {
    color: #ccc;
  }
  .lesson-content :deep(.markdown-body) code {
    background: #2a2a2a;
    color: #e0e0e0;
  }
  .lesson-content :deep(.markdown-body) th {
    background: #2a2a2a;
  }
  .lesson-content :deep(.markdown-body) th,
  .lesson-content :deep(.markdown-body) td {
    border-color: #444;
    color: #ccc;
  }
  .lesson-content :deep(.markdown-body) h2 {
    border-bottom-color: #333;
  }
  .lesson-content :deep(.markdown-body) blockquote {
    background: #1a1a2e;
  }
  .no-content-prompt h4 {
    color: #ddd;
  }
  .modal-footer {
    border-color: #333;
  }
  .close-btn {
    background: #333;
    color: #ccc;
  }
  .btn-outline {
    background: #2a2a2a;
    border-color: #444;
    color: #aaa;
  }
  .detail-label {
    color: #888;
  }
  .badge-modal {
    background: #1e1e1e;
  }
  .new-badge-item {
    background: #2a2a2a;
  }
}
</style>
