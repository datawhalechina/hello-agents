import { createRouter, createWebHashHistory } from 'vue-router'

import ChatView from '../views/ChatView.vue'
import DashboardView from '../views/DashboardView.vue'
import PlanView from '../views/PlanView.vue'
import TraceView from '../views/TraceView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'chat', component: ChatView, meta: { title: '健康对话' } },
  { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { title: '指标趋势' } },
  { path: '/plan', name: 'plan', component: PlanView, meta: { title: '运动计划' } },
  { path: '/trace', name: 'trace', component: TraceView, meta: { title: 'Agent 链路' } },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
