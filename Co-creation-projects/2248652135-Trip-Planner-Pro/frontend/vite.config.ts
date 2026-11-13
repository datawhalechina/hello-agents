import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import fs from 'fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    https: {
      cert: fs.readFileSync(resolve(__dirname, '../backend/certs/cert.pem')),
      key: fs.readFileSync(resolve(__dirname, '../backend/certs/key.pem')),
    },
    proxy: {
      '/api': {
        target: 'https://localhost:8000',
        changeOrigin: true,
        secure: false,  // 开发环境使用自签名证书，设为false跳过校验
      }
    }
  }
})

