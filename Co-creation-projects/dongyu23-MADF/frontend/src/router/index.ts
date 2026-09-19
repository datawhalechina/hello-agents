import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BasicLayout from '@/layouts/BasicLayout.vue'
import UserLayout from '@/layouts/UserLayout.vue'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import PersonaView from '@/views/PersonaView.vue'
import ForumListView from '@/views/ForumListView.vue'
import ForumDetailView from '@/views/ForumDetailView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/auth',
      component: UserLayout,
      redirect: '/auth/login',
      children: [
        {
          path: 'login',
          name: 'login',
          component: LoginView
        },
        {
          path: 'register',
          name: 'register',
          component: RegisterView
        }
      ]
    },
    {
      path: '/',
      component: BasicLayout,
      redirect: '/dashboard',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: HomeView
        },
        {
          path: 'personas',
          name: 'personas',
          component: PersonaView
        },
        {
          path: 'forums',
          name: 'forums',
          component: ForumListView
        },
        {
          path: 'forums/:id',
          name: 'forum-detail',
          component: ForumDetailView
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard'
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  
  if (to.path.startsWith('/auth') && authStore.token) {
    next('/dashboard')
    return
  }
  
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.token) {
      next('/auth/login')
      return
    }
  }
  
  next()
})

export default router
