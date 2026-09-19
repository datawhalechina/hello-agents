/**
 * 共享TypeScript类型定义
 * 避免在多个组件中重复定义相同的接口
 */

// ===== 学习路径相关 =====

export interface Lesson {
  id: string
  title: string
  description: string
  type: string
  duration_minutes: number
  is_completed: boolean
  language?: string
}

export interface Module {
  id: string
  title: string
  description: string
  icon: string
  order: number
  lessons: Lesson[]
  status: string
  progress: number
}

export interface PathOverview {
  path: string
  title: string
  description: string
  icon: string
  total_modules: number
  total_lessons: number
}

export interface PathDetail {
  path: string
  title: string
  description: string
  icon: string
  modules: Module[]
  total_lessons: number
  completed_lessons: number
  progress: number
}

// ===== 教练相关 =====

export interface CoachRecommendation {
  type: string
  title: string
  description: string
  module_id?: string
  lesson_id?: string
  priority: number
}

export interface CoachData {
  greeting: string
  recommendations: CoachRecommendation[]
  encouragement: string
  stats: Record<string, any>
}

// ===== 评估相关 =====

export interface AssessmentQuestion {
  id: string
  category: string
  difficulty: number
  content: string
  options: string[]
  correct_answer: string
  explanation: string
}

export interface AssessmentResult {
  user_id: string
  path_type: string
  total_questions: number
  correct_count: number
  score: number
  level: string
  category_scores: Record<string, number>
  recommended_start_module: string
  completed_at: string
  is_current: boolean
}

export interface AssessmentRecord {
  id: string
  path_type: string
  score: number
  level: string
  category_scores: Record<string, number>
  completed_at: string
}

// ===== 聊天相关 =====

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  agent_name?: string
}

export interface LearningContext {
  message: string
  path_type: string
  user_level: string | null
  skill_levels: Record<string, number> | null
  lesson_id?: string
  module_id?: string
  lesson_title?: string
  module_title?: string
}

// ===== 用户进度相关 =====

export interface UserProgress {
  user_id: string
  current_path: string | null
  completed_modules: string[]
  completed_lessons: string[]
  current_module: string | null
  current_lesson: string | null
  started_at: string | null
  last_activity_at: string | null
  total_study_minutes: number
}

// ===== Agent相关 =====

export interface AgentNode {
  id: string
  type: string
  name: string
  status: 'idle' | 'active' | 'processing' | 'completed' | 'error'
  lastUsed?: string
  messageCount: number
}
