/** v1.1 端到端测试：团队协作、子团队、协作任务、AI 推荐与通知中心。 */

import { expect, test, type Page } from '@playwright/test'

import { DEMO_ADMIN_ACCOUNT, captureScreenshot, loginAs, navigateBySidebar } from './helpers'

/** 读取当前登录 token（用于直接调用 API 定位演示数据）。 */
async function readStoredToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => window.localStorage.getItem('tms.token'))
  return String(token)
}

test.describe('v1.1 Team Collaboration', () => {
  test('collaboration center shows my collaborations, pending confirmation, and team directory', async ({
    page,
  }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Collaborations')
    await expect(page.getByRole('heading', { name: 'Collaboration Center', level: 1 }).first()).toBeVisible()
    await expect(page.getByRole('tab', { name: 'My Collaborations' })).toBeVisible()
    await expect(page.getByRole('tab', { name: /Pending Confirmation/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Team Directory' })).toBeVisible()
    await expect(page.getByText('Product Design Team').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'collaboration-center.png')
    await page.getByRole('tab', { name: /Pending Confirmation/ }).click()
    await expect(page.getByText('Product Design Team').first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: 'Confirm Request' }).first()).toBeVisible()
    await captureScreenshot(page, 'collaboration-pending.png')
    await page.getByRole('tab', { name: 'Team Directory' }).click()
    await expect(page.getByText('Product Design Team').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'collaboration-directory.png')
  })

  test('team details show the sub-teams and collaborations tabs', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Teams')
    await page.getByRole('link', { name: /Enter Team/ }).first().click()
    await expect(page.getByRole('tab', { name: 'Sub-teams' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Collaborations' })).toBeVisible()
    await page.getByRole('tab', { name: 'Sub-teams' }).click()
    await expect(page.getByText('Frontend Team').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'team-subteams.png')
    await page.getByRole('tab', { name: 'Collaborations' }).click()
    await expect(page.getByText('Product Design Team').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'team-collaborations.png')
  })

  test('collaboration task details show the phase and two-stage review info', async ({ page, request }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    const token = await readStoredToken(page)
    const authorizationHeader = { Authorization: 'Bearer ' + token }
    const collaborationResponse = await request.get('/api/v1/collaborations?page=1&pageSize=20', {
      headers: authorizationHeader,
    })
    expect(collaborationResponse.ok()).toBeTruthy()
    const collaborationPayload = await collaborationResponse.json()
    const activeCollaboration = collaborationPayload.items.find(
      (item: { status: string }) => item.status === 'active',
    )
    expect(activeCollaboration).toBeTruthy()
    const tasksResponse = await request.get(
      '/api/v1/collaborations/' + String(activeCollaboration.id) + '/tasks?page=1&pageSize=20',
      { headers: authorizationHeader },
    )
    expect(tasksResponse.ok()).toBeTruthy()
    const taskPayload = await tasksResponse.json()
    expect(taskPayload.items.length).toBeGreaterThan(0)
    const taskId = taskPayload.items[0].id
    await page.goto('/collaboration-tasks/' + String(taskId))
    await expect(page.getByText(/Collaboration stage/).first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Initiating Unit').first()).toBeVisible()
    await captureScreenshot(page, 'collaboration-task-detail.png')
  })

  test('receiver liaison sees the collaboration task confirmation entry', async ({ page, request }) => {
    await loginAs(page, { username: 'designerB', password: 'Demo@123456' })
    const token = await readStoredToken(page)
    const authorizationHeader = { Authorization: 'Bearer ' + token }
    const collaborationResponse = await request.get('/api/v1/collaborations?page=1&pageSize=20', {
      headers: authorizationHeader,
    })
    expect(collaborationResponse.ok()).toBeTruthy()
    const collaborationPayload = await collaborationResponse.json()
    const activeCollaborations: { id: number }[] = collaborationPayload.items.filter(
      (item: { status: string }) => item.status === 'active',
    )
    expect(activeCollaborations.length).toBeGreaterThan(0)
    // 遍历全部进行中的协作，定位接收方待确认的协作任务（列表顺序可能变化）
    let pendingTask: { id: number } | null = null
    for (const activeCollaboration of activeCollaborations) {
      const tasksResponse = await request.get(
        '/api/v1/collaborations/' + String(activeCollaboration.id) + '/tasks?page=1&pageSize=20',
        { headers: authorizationHeader },
      )
      expect(tasksResponse.ok()).toBeTruthy()
      const taskPayload = await tasksResponse.json()
      const foundTask = taskPayload.items.find(
        (item: { collaborationPhase: string }) =>
          item.collaborationPhase === 'pendingConfirmation' && item.canConfirmTask === true,
      )
      if (foundTask) {
        pendingTask = foundTask
        break
      }
    }
    if (pendingTask === null) {
      throw new Error('No collaboration task in pending confirmation phase was found for the receiver liaison.')
    }
    await page.goto('/collaboration-tasks/' + String(pendingTask.id))
    await expect(page.getByRole('button', { name: /Process Collaboration Task/ })).toBeVisible({
      timeout: 20_000,
    })
    await captureScreenshot(page, 'collaboration-task-confirm.png')
  })
})

test.describe('v1.1 AI and Notifications', () => {
  test('AI recommendation panel returns candidate members and scores', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Teams')
    await page.getByRole('link', { name: /Enter Team/ }).first().click()
    await page.getByRole('tab', { name: 'Tasks' }).click()
    await page.getByRole('button', { name: 'Publish Task' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByLabel('Task Title *').fill('Implement task board statistics API')
    await page.getByRole('button', { name: 'Get Recommendations' }).click()
    await expect(page.getByText(/Candidates: \d+/).first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/Match rate/).first()).toBeVisible()
    await captureScreenshot(page, 'ai-recommend.png')
    await page.getByRole('button', { name: 'Cancel' }).click()
  })

  test('notification center shows demo notifications and AI dispatch status', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await expect(page.getByRole('button', { name: /Notifications/ }).first()).toBeVisible()
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Notification Center' }).first()).toBeVisible()
    await expect(page.getByText('Collaboration is now active').first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('AI Dispatch Status').first()).toBeVisible()
    await captureScreenshot(page, 'notifications.png')
    await page.getByRole('tab', { name: 'Unread' }).click()
    await expect(page.getByRole('tab', { name: 'Unread' })).toHaveAttribute('aria-selected', 'true')
  })
})
