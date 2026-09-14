import { createRouter, createWebHistory } from 'vue-router'
import ChatView from './views/ChatView.vue'
import SessionsView from './views/SessionsView.vue'
import MemoryView from './views/MemoryView.vue'
import IdentityView from './views/IdentityView.vue'
import ReportsView from './views/ReportsView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: ChatView },
    { path: '/sessions', name: 'sessions', component: SessionsView },
    { path: '/memory', name: 'memory', component: MemoryView },
    { path: '/identity', name: 'identity', component: IdentityView },
    { path: '/reports', name: 'reports', component: ReportsView },
  ],
})
