/** v1.1.1 端到端测试：系统设置中的 AI 配置与连通性测试。 */

import { expect, test, type Page } from '@playwright/test'

import { DEMO_ADMIN_ACCOUNT, SUPER_ADMIN_ACCOUNT, captureScreenshot, loginAs, navigateBySidebar } from './helpers'

/** 读取当前登录 token。 */
async function readStoredToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => window.localStorage.getItem('tms.token'))
  return String(token)
}

test.describe('v1.1.1 System Settings · AI Configuration', () => {
  test('global admin can view and test AI configuration connectivity', async ({ page }) => {
    await loginAs(page, SUPER_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Settings')
    await expect(page.getByRole('heading', { name: 'System Settings' }).first()).toBeVisible()
    await expect(page.getByText('AI Configuration').first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Current Configuration').first()).toBeVisible()
    await expect(page.getByLabel('Dispatch Mode')).toBeVisible()
    await expect(page.getByLabel('LLM Base URL')).toBeVisible()
    await expect(page.getByLabel('API Key')).toBeVisible()
    await page.getByRole('button', { name: 'Test Connectivity' }).click()
    await expect(page.getByText('Connectivity Test Result')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Local Rule Engine', { exact: true })).toBeVisible()
    await expect(page.getByText('Available', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('LLM', { exact: true })).toBeVisible()
    await captureScreenshot(page, 'ai-config-settings.png')
  })

  test('admin can change the dispatch mode and persist it', async ({ page, request }) => {
    await loginAs(page, SUPER_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Settings')
    await expect(page.getByLabel('Dispatch Mode')).toBeVisible({ timeout: 20_000 })
    await page.getByLabel('Dispatch Mode').selectOption({ label: 'Local Only' })
    await page.getByRole('button', { name: 'Save Configuration' }).click()
    await expect(page.getByText('AI configuration saved')).toBeVisible({ timeout: 20_000 })
    const token = await readStoredToken(page)
    const authorizationHeader = { Authorization: 'Bearer ' + token }
    const configResponse = await request.get('/api/v1/settings/ai-config', {
      headers: authorizationHeader,
    })
    expect(configResponse.ok()).toBeTruthy()
    const configPayload = await configResponse.json()
    expect(configPayload.dispatchMode).toBe('LOCAL_ONLY')
    // 恢复演示环境默认调度模式，避免影响其他用例与演示数据
    const restoreResponse = await request.put('/api/v1/settings/ai-config', {
      headers: authorizationHeader,
      data: { dispatchMode: 'LOCAL_FIRST' },
    })
    expect(restoreResponse.ok()).toBeTruthy()
  })

  test('standard user can only view the AI configuration', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Settings')
    await expect(page.getByText('AI Configuration').first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Only global admins can modify the AI configuration')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save Configuration' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Test Connectivity' })).toHaveCount(0)
  })
})
