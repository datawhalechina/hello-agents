import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev server proxies /api to the FastAPI backend so the frontend never
// hard-codes a backend URL (and avoids CORS issues during development).
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('@element-plus/icons-vue')) return 'element-icons'
          if (id.includes('element-plus')) return 'element-plus'
          if (id.includes('dompurify') || id.includes('marked')) return 'markdown'
          if (id.includes('/vue/') || id.includes('vue-router') || id.includes('pinia')) {
            return 'vue-vendor'
          }
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
