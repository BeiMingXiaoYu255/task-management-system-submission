/** 端到端测试：登录、仪表盘、主题切换、侧边栏导航。 */

import { expect, test } from '@playwright/test'

import { DEMO_ADMIN_ACCOUNT, captureScreenshot, loginAs } from './helpers'

test.describe('Authentication and Dashboard', () => {
  test('demo admin signs in, lands on the dashboard, and sees statistics', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await expect(page.getByText('Loading dashboard data ...')).toBeHidden({ timeout: 20_000 })
    await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 }).first()).toBeVisible()
    // 侧边栏导航项齐全
    for (const navigationLabel of ['Dashboard', 'Teams', 'To-dos', 'Tasks', 'Profile', 'Settings']) {
      await expect(page.getByRole('link', { name: navigationLabel, exact: true })).toBeVisible()
    }
    // 普通用户不显示管理后台入口
    await expect(page.getByRole('link', { name: 'Admin Console', exact: true })).toHaveCount(0)
    await captureScreenshot(page, 'dashboard-light.png')
  })

  test('dark mode applies across the app and can be screenshotted', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await captureScreenshot(page, 'dashboard-dark.png')
    await page.getByRole('button', { name: 'Switch to light mode' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  })

  test('sticky to-dos page renders standalone without the sidebar', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await page.goto('/sticky')
    await expect(page.getByRole('heading', { name: 'Sticky To-dos', level: 1 })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toHaveCount(0)
    await captureScreenshot(page, 'sticky.png')
  })

  test('unauthenticated access to a protected page redirects to sign in', async ({ page }) => {
    await page.goto('/todos')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: 'Sign In' }).first()).toBeVisible()
  })

  test('signing in with a wrong password shows an error alert', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username').fill('demoAdmin')
    await page.getByLabel('Password').fill('WrongPassword123')
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 15_000 })
    await expect(page).toHaveURL(/\/login/)
  })
})
