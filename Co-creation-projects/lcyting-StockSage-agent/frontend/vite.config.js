import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    // 开发服启动后预转换常用页面，首次打开/切换更快
    warmup: {
      clientFiles: [
        './src/views/Dashboard.vue',
        './src/views/StockAnalysis.vue',
        './src/views/StockScreener.vue',
        './src/views/NewsCenter.vue',
        './src/views/Simulation.vue',
      ],
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
