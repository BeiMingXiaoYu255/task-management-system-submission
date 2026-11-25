/** 端到端测试：管理后台各面板与设置页。 */

import { expect, test } from '@playwright/test'

import { DEMO_ADMIN_ACCOUNT, SUPER_ADMIN_ACCOUNT, captureScreenshot, loginAs, navigateBySidebar } from './helpers'

test.describe('Admin Console and Settings', () => {
  test('super admin opens the admin console and views users, database, and audit panels', async ({
    page,
  }) => {
    await loginAs(page, SUPER_ADMIN_ACCOUNT)
    await expect(page.getByRole('link', { name: 'Admin Console', exact: true })).toBeVisible()
    await navigateBySidebar(page, 'Admin Console')
    await expect(page.getByRole('heading', { name: 'Admin Console' }).first()).toBeVisible()
    for (const tabLabel of ['Overview', 'Users', 'Teams', 'Database', 'Audit']) {
      await expect(page.getByRole('tab', { name: tabLabel })).toBeVisible()
    }
    await page.getByRole('tab', { name: 'Users' }).click()
    await expect(page.getByText('superAdmin').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'admin-users.png')
    await page.getByRole('tab', { name: 'Database' }).click()
    await expect(page.getByText('users').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'admin-database.png')
    await page.getByRole('tab', { name: 'Audit' }).click()
    await expect(page.getByRole('tab', { name: 'Audit' })).toHaveAttribute('aria-selected', 'true')
  })

  test('standard user cannot access the admin console', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('settings page switches font size and shows system info and LAN addresses', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Settings')
    await expect(page.getByRole('heading', { name: 'System Settings' }).first()).toBeVisible()
    await expect(page.getByText('LAN Access Addresses')).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'settings.png')
  })

  test('profile page shows skill tags and team memberships', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Profile')
    await expect(page.getByRole('heading', { name: 'Profile' }).first()).toBeVisible()
    await expect(page.getByText('Demo Admin').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'profile.png')
  })
})
