import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright 端到端测试配置。
 *
 * 前置条件：
 *   1. 后端运行在 http://127.0.0.1:8765 并托管 Frontend/dist（npm run build 已执行）；
 *   2. 开发数据库已启动（scripts/startLocalRuntime.ps1）且已写入演示数据。
 * 运行：cd Frontend; npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },
  projects: [
    {
      // 使用系统安装的 Microsoft Edge（channel: 'msedge'），避免首次运行再下载 Chromium；
      // 若环境中没有 Edge，可将 channel 改为 'chrome' 或先执行 npx playwright install chromium。
      name: 'edge',
      use: { ...devices['Desktop Chrome'], channel: 'msedge', viewport: { width: 1440, height: 900 } },
    },
  ],
})
