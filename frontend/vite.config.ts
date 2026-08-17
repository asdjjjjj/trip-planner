import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 默认部署在站点子路径 /trip-planner/ 下；Vercel 独立部署时设置环境变量 VITE_BASE_PATH=/
  base: process.env.VITE_BASE_PATH || '/trip-planner/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
