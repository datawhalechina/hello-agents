// 基础数据模型
export interface Location {
  lat: number
  lng: number
}

// --- 核心业务模型 ---

// 与后端 Attraction 模型对齐
export interface Attraction {
  name: string
  type: string
  rating: number | string
  suggested_duration_hours?: number | null
  description: string
  address: string
  location?: Location
  image_urls: string[]
  ticket_price: number | string
  // 前端扩展字段（用于编辑）
  notes?: string // 用户备注
  actual_cost?: number // 实际花费
}

// 与后端 Hotel 模型对齐
export interface Hotel {
  name: string
  address: string
  location?: Location
  price: number | string
  rating: number | string
  distance_to_main_attraction_km?: number | null
}

// 与后端 Dining 模型对齐
export interface Dining {
  name: string
  address: string
  location?: Location
  cost_per_person: number | string
  rating: number | string
}

export interface Weather {
  date: string
  day_weather: string
  night_weather: string
  day_temp: string
  night_temp: string
  day_wind?: string | null
  night_wind?: string | null
}

// 行程规划请求模型
export interface TripPlanRequest {
  destination: string
  start_date: string
  end_date: string
  preferences: string[]
  hotel_preferences: string[]
  budget: string
}

// 预算拆分（与后端 BudgetBreakdown 对齐）
export interface BudgetBreakdown {
  transport_cost: number
  dining_cost: number
  hotel_cost: number
  attraction_ticket_cost: number
  total: number
}

// 单日预算（与后端 DailyBudget 对齐）
export interface DailyBudget {
  transport_cost: number
  dining_cost: number
  hotel_cost: number
  attraction_ticket_cost: number
  total: number
}

// 每日行程计划（与后端 DailyPlan 对齐）
export interface DailyPlan {
  day: number
  theme: string
  weather?: Weather
  recommended_hotel?: Hotel | null
  attractions: Attraction[]
  dinings: Dining[]
  budget: DailyBudget
}

// 行程规划响应模型（与后端 TripPlanResponse 对齐）
export interface TripPlanResponse {
  trip_title: string
  total_budget: BudgetBreakdown
  hotels: Hotel[]
  days: DailyPlan[]
}

// 表单数据类型
export interface TripFormData {
  destination: string
  dateRange: [string, string]
  preferences: string[]
  hotelPreferences: string[]
  budget: string
}

// 预算明细类型（前端展示用）
export interface BudgetDetail {
  category: string
  amount: number
  items: {
    name: string
    cost: number
  }[]
}

// 地图点位类型（前端内部使用，用于 MapView 展示行程）
export interface MapPoint {
  name: string
  type: 'attraction' | 'dining' | 'hotel' | 'transport' | string
  description?: string
  cost?: number
  location?: Location
}

// 导出选项类型
export interface ExportOptions {
  format: 'pdf' | 'image'
  includeBudget: boolean
  includeMap: boolean
}

// === 用户认证相关类型 ===

// 用户登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 用户注册请求
export interface RegisterRequest {
  username: string
  password: string
}

// 用户信息
export interface User {
  user_id: string
  username: string
  user_type: string  // 'registered'
  phone?: string
  gender?: 'male' | 'female' | 'other'
  birthday?: string
  bio?: string
  travel_preferences?: string[]
  avatar_url?: string
}

// 用户资料更新请求
export interface UpdateProfileRequest {
  username?: string
  phone?: string
  gender?: 'male' | 'female' | 'other'
  birthday?: string
  bio?: string
  travel_preferences?: string[]
  avatar_url?: string
}

// 修改密码请求
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

// 认证令牌响应
export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

// 认证状态
export interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
}
