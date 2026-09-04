import { createRouter, createWebHistory } from 'vue-router'
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/search' },
    { path: '/search', component: () => import('@/views/SearchAgent.vue'), name: 'search' },
    { path: '/daily', component: () => import('@/views/DailyArxiv.vue'), name: 'daily' },
    { path: '/library/read/:id', component: () => import('@/views/PaperReader.vue'), name: 'library-read' },
    { path: '/library', component: () => import('@/views/Library.vue'), name: 'library' },
    { path: '/graph', component: () => import('@/views/KnowledgeGraph.vue'), name: 'graph' },
  ],
})
export default router