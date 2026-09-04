import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '智能行程规划', requiresAuth: false }
  },
  {
    path: '/my-trips',
    name: 'MyTrips',
    component: () => import('@/views/MyTrips.vue'),
    meta: { title: '我的行程', requiresAuth: true }
  },
  {
    path: '/result',
    name: 'Result',
    component: () => import('@/views/Result.vue'),
    meta: { title: '行程详情', requiresAuth: true }
  },
  {
    path: '/edit',
    name: 'EditPlan',
    component: () => import('@/views/EditPlan.vue'),
    meta: { title: '编辑行程', requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '用户登录', requiresAuth: false }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { title: '个人资料', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 延迟初始化store以避免循环依赖
router.beforeEach(async (to, _from, next) => {
  try {
    // 动态导入store以避免循环依赖
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    
    // 更新页面标题
    if (to.meta.title) {
      document.title = `${to.meta.title} - 智能旅行助手`
    }
    
    // 检查是否需要认证
    if (to.meta.requiresAuth) {
      // 如果未认证，重定向到登录页面
      if (!authStore.isAuthenticated) {
        next('/login')
        return
      }
    }
    
    // 如果已认证且访问登录页面，重定向到首页
    if (to.path === '/login' && authStore.isAuthenticated) {
      next('/')
      return
    }
    
    next()
  } catch (error) {
    console.error('路由守卫初始化失败:', error)
    next()
  }
})

export default router
