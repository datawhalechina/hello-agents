import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'

function parsePort(raw: string | undefined, fallback: number): number {
  const n = Number.parseInt(String(raw ?? '').trim(), 10)
  if (!Number.isFinite(n) || n < 1 || n > 65535) return fallback
  return n
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendPort = parsePort(
    process.env.BACKEND_PORT || env.BACKEND_PORT || env.VITE_BACKEND_PORT,
    8000,
  )
  const frontendPort = parsePort(
    process.env.FRONTEND_PORT || env.FRONTEND_PORT || env.VITE_DEV_PORT,
    5173,
  )
  const backend = `http://127.0.0.1:${backendPort}`

  return {
    plugins: [vue()],
    resolve: { alias: { '@': resolve(process.cwd(), 'src') } },
    server: {
      host: '127.0.0.1',
      port: frontendPort,
      strictPort: true,
      open: '/',
      proxy: {
        '/api': { target: backend, changeOrigin: true, timeout: 420000, proxyTimeout: 420000 },
        '/health': { target: backend, changeOrigin: true, timeout: 420000, proxyTimeout: 420000 },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/ant-design-vue')) {
              if (id.includes('/vc-table/') || id.includes('/table/')) return 'antd-table'
              if (id.includes('/vc-select/') || id.includes('/select/')) return 'antd-select'
              if (id.includes('/vc-picker/') || id.includes('/date-picker/')) return 'antd-picker'
              return 'antd'
            }
            if (id.includes('node_modules/katex')) return 'katex'
          },
        },
      },
    },
  }
})
