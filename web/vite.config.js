import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发期可选：把 /api 代理到后端，配合 VITE_API_BASE_URL=""（同源请求）使用
const API_TARGET = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:9135'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true
      }
    }
  }
})
