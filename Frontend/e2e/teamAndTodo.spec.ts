/** 端到端测试：团队列表、团队详情、成员与任务页面、待办清单。 */

import { expect, test } from '@playwright/test'

import { DEMO_ADMIN_ACCOUNT, captureScreenshot, loginAs, navigateBySidebar } from './helpers'

test.describe('Teams and To-dos', () => {
  test('team list shows the demo team and opens team details', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Teams')
    await expect(page.getByRole('heading', { name: 'My Teams' }).first()).toBeVisible()
    await expect(page.getByText('Minimal R&D Team').first()).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'teams.png')
    await page.getByRole('link', { name: /Enter Team/ }).first().click()
    await expect(page).toHaveURL(/\/teams\/\d+/)
    // 五个页签齐全
    for (const tabLabel of ['Overview', 'Tasks', 'Members', 'Levels', 'Settings']) {
      await expect(page.getByRole('tab', { name: tabLabel })).toBeVisible()
    }
    await page.getByRole('tab', { name: 'Tasks' }).click()
    await expect(page.getByRole('button', { name: 'Publish Task' })).toBeVisible({ timeout: 20_000 })
    await captureScreenshot(page, 'team-tasks.png')
    await page.getByRole('tab', { name: 'Members' }).click()
    await expect(page.getByRole('tab', { name: 'Members' })).toHaveAttribute('aria-selected', 'true')
    await captureScreenshot(page, 'team-members.png')
  })

  test('to-do list loads and shows the filter area and list', async ({ page }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'To-dos')
    await expect(page.getByRole('heading', { name: 'My To-dos' }).first()).toBeVisible()
    await expect(page.getByText('Loading to-dos...')).toBeHidden({ timeout: 20_000 })
    await captureScreenshot(page, 'todos.png')
  })

  test('create team dialog submits and shows the new team card', async ({ page, request }) => {
    await loginAs(page, DEMO_ADMIN_ACCOUNT)
    await navigateBySidebar(page, 'Teams')
    await expect(page.getByRole('heading', { name: 'My Teams' }).first()).toBeVisible()
    await page.getByRole('button', { name: 'Create Team' }).first().click()
    await expect(page.getByRole('dialog')).toBeVisible()
    const uniqueTeamName = 'E2E Automation Team ' + Date.now()
    await page.getByLabel('Team Name *').fill(uniqueTeamName)
    await page.getByRole('dialog').getByRole('button', { name: 'Create Team' }).click()
    await expect(page.getByText('Team created. Waiting for Global Admin certification.')).toBeVisible({
      timeout: 20_000,
    })
    await expect(page.getByText(uniqueTeamName).first()).toBeVisible({ timeout: 20_000 })
    // 用例收尾：通过接口删除本次创建的测试团队，避免污染演示数据
    const token = await page.evaluate(() => window.localStorage.getItem('tms.token'))
    const headers = { Authorization: 'Bearer ' + String(token) }
    const teamsResponse = await request.get('/api/v1/teams', { headers })
    const teamsPayload = await teamsResponse.json()
    const createdTeam = (teamsPayload as { id: number; name: string }[]).find(
      (teamItem) => teamItem.name === uniqueTeamName,
    )
    if (createdTeam) {
      await request.delete('/api/v1/teams/' + createdTeam.id, {
        headers,
        data: { confirmName: uniqueTeamName },
      })
    }
  })
})
