/** Playwright 端到端测试公共辅助函数。 */

import { expect, type Page } from '@playwright/test'

/** 演示数据中的团队管理员账号。 */
export const DEMO_ADMIN_ACCOUNT = { username: 'demoAdmin', password: 'Demo@123456' }

/** 内置超级用户账号。 */
export const SUPER_ADMIN_ACCOUNT = { username: 'superAdmin', password: 'SuperAdmin@123' }

/** 通过登录页完成登录并等待进入仪表盘。 */
export async function loginAs(
  page: Page,
  account: { username: string; password: string },
): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Username').fill(account.username)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign In', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
  await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 }).first()).toBeVisible()
}

/** 通过侧边栏导航跳转到指定页面。 */
export async function navigateBySidebar(page: Page, navigationLabel: string): Promise<void> {
  await page.getByRole('link', { name: navigationLabel, exact: true }).click()
}

/** 截取页面截图到 docs/screenshots 目录（用于交付文档与验收记录）。 */
export async function captureScreenshot(page: Page, fileName: string): Promise<void> {
  const screenshotDirectory = '../docs/screenshots'
  const fileSystem = await import('node:fs')
  fileSystem.mkdirSync(screenshotDirectory, { recursive: true })
  await page.waitForTimeout(3200)
  await page.screenshot({ path: screenshotDirectory + '/' + fileName, fullPage: true })
}
