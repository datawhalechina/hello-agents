/**
 * 共享工具函数
 * 支持中英文切换，通过 langStore 获取翻译
 */
import { useLangStore } from '../stores/langStore'

// 延迟获取 langStore（确保 Pinia 已安装）
function getLang() {
  try {
    return useLangStore()
  } catch {
    return null
  }
}

function t(key: string): string {
  const lang = getLang()
  return lang ? lang.t(key) : key
}

// ===== 分类名称 =====
export function getCategoryName(category: string): string {
  return t(`helpers.categories.${category}`)
}

// ===== 水平文本 =====
export function getLevelText(level: string): string {
  return t(`helpers.levels.${level}`)
}

// ===== 状态文本 =====
export function getStatusText(status: string): string {
  return t(`helpers.statuses.${status}`)
}

// ===== 课程类型图标（图标不需要翻译） =====
export const LESSON_TYPE_ICONS: Record<string, string> = {
  theory: '📖',
  practice: '💻',
  quiz: '❓',
  project: '🚀'
}

export function getLessonTypeIcon(type: string): string {
  return LESSON_TYPE_ICONS[type] || '📝'
}

// ===== 课程类型文本 =====
export function getLessonTypeText(type: string): string {
  return t(`helpers.lessonTypes.${type}`)
}

// ===== 推荐类型图标（图标不需要翻译） =====
export const REC_ICONS: Record<string, string> = {
  next_lesson: '➡️',
  review: '🔄',
  practice: '💪',
  challenge: '🏆',
  select_path: '🎯'
}

export function getRecIcon(type: string): string {
  return REC_ICONS[type] || '💡'
}

// ===== Agent图标（图标不需要翻译） =====
export const AGENT_ICONS: Record<string, string> = {
  '编程导师': '👨‍🏫',
  '调试助手': '🐛',
  '代码审查员': '🔍',
  '架构师': '🏗️',
  '学习教练': '🎯',
  'Tutor': '👨‍🏫',
  'Debugger': '🐛',
  'Reviewer': '🔍',
  'Architect': '🏗️',
  'Coach': '🎯',
}

// ===== Agent类型映射 =====
export const AGENT_TYPES: Record<string, string> = {
  '编程导师': 'tutor',
  '调试助手': 'debug',
  '代码审查员': 'review',
  '架构师': 'arch',
  '学习教练': 'coach',
  'Tutor': 'tutor',
  'Debugger': 'debug',
  'Reviewer': 'review',
  'Architect': 'arch',
  'Coach': 'coach',
}

export function getAgentIcon(agentName?: string): string {
  return AGENT_ICONS[agentName || ''] || '🤖'
}

export function getAgentType(agentName?: string): string {
  return AGENT_TYPES[agentName || ''] || 'default'
}

// ===== 分数CSS类名（不需要翻译） =====
export function getScoreClass(score: number): string {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  if (score >= 40) return 'fair'
  return 'poor'
}

export function getScoreBarClass(score: number): string {
  return getScoreClass(score)
}

// ===== 难度文本 =====
export function getDifficultyText(level: number): string {
  return t(`helpers.difficulty.${level}`)
}

// ===== 难度CSS类名（不需要翻译） =====
export function getDifficultyClass(level: number): string {
  if (level <= 2) return 'easy'
  if (level <= 3) return 'medium'
  return 'hard'
}

// ===== 模块名称 =====
export function getModuleName(moduleId: string): string {
  return t(`helpers.modules.${moduleId}`)
}

// ===== 路径标题 =====
export function getPathTitle(path: string): string {
  const key = `helpers.categories.${path}`
  const result = t(key)
  // 如果翻译不存在，回退到硬编码
  if (result === key) {
    const fallbacks: Record<string, string> = {
      frontend: 'Frontend Development / 前端开发',
      backend: 'Backend Development / 后端开发',
      fullstack: 'Fullstack Development / 全栈开发'
    }
    return fallbacks[path] || path
  }
  return result
}

// ===== 选项工具 =====
export function getOptionText(option: string): string {
  return option.replace(/^[A-D]\.\s*/, '')
}

export function getOptionLetter(index: number): string {
  return String.fromCharCode(65 + index)
}

// ===== Agent状态文本 =====
export function getAgentStatusText(status: string): string {
  return t(`helpers.agentStatus.${status}`)
}

// ===== 题目类型文本 =====
export function getQuestionTypeText(type: string): string {
  return t(`helpers.questionTypes.${type}`)
}
