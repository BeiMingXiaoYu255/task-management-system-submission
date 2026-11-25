import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/** Vitest 单元测试配置：jsdom 环境 + 测试初始化文件。 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // 仅收集 src 下的单元测试，避免把 e2e 目录的 Playwright 用例当 vitest 用例收集
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
