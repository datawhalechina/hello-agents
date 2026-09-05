import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Chat from '../views/Chat.vue'
import Orchestration from '../views/Orchestration.vue'
import Learning from '../views/Learning.vue'
import Assessment from '../views/Assessment.vue'
import Dashboard from '../views/Dashboard.vue'
import Login from '../views/Login.vue'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: Login },
  { path: '/', name: 'Chat', component: Chat },
  { path: '/orchestration', name: 'Orchestration', component: Orchestration },
  { path: '/learning', name: 'Learning', component: Learning },
  { path: '/assessment', name: 'Assessment', component: Assessment },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const userId = localStorage.getItem('currentUserId')
  if (to.name !== 'Login' && !userId) {
    return { name: 'Login' }
  }
})

export default router
