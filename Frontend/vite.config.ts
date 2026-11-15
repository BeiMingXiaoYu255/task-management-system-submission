import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/** Vite 构建配置：开发端口 5173，构建产物输出 dist。 */
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 800,
  },
})
