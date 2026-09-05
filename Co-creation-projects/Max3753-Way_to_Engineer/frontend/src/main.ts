import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import App from './App.vue'
import router from './router'
import './style.css'
import './dark-theme-overrides.css'
import './styles/highlight-theme.css'

// Apply saved theme immediately to prevent flash of wrong theme
const savedTheme = localStorage.getItem('theme') || 'light'
document.documentElement.setAttribute('data-theme', savedTheme)

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Initialize language preference from localStorage
import { useLangStore } from './stores/langStore'
const langStore = useLangStore()
langStore.init()

app.mount('#app')
