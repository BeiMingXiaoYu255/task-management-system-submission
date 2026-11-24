/**
 * AppShell 冒烟测试：验证侧边栏导航、顶栏标题、管理员入口与主题应用逻辑可正常挂载。
 * 通过 mock 认证与设置接口，避免测试依赖真实后端。
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AppShell from '../components/layout/AppShell'
import { AuthProvider } from '../context/AuthContext'
import { ThemeProvider } from '../context/ThemeContext'
import { ToastProvider } from '../context/ToastContext'
import type { CurrentUser } from '../types/auth'

/** hoisted 的测试数据：供 vi.mock 工厂函数在模块提升后安全引用。 */
const { mockCurrentUser, mockGetSettings } = vi.hoisted(() => {
  const currentUser: CurrentUser = {
    user: {
      id: 9,
      username: 'globalAdminUser',
      nickname: 'Admin User',
      avatar: null,
      globalRole: 'globalAdmin',
      email: null,
      phone: null,
      bio: null,
      createdAt: '2026-01-01T00:00:00',
      skills: [],
    },
    teams: [],
  }
  return { mockCurrentUser: currentUser, mockGetSettings: vi.fn() }
})

vi.mock('../api/authApi', () => ({
  getCurrentUser: vi.fn(() => Promise.resolve(mockCurrentUser)),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../api/settingApi', () => ({
  getSettings: mockGetSettings,
  updateSettings: vi.fn(),
  deleteAccount: vi.fn(),
}))

beforeEach(() => {
  localStorage.setItem('tms.token', 'test-token')
  mockGetSettings.mockResolvedValue({ theme: 'light', fontSize: 'medium', fontFamily: 'system' })
})

afterEach(() => {
  localStorage.clear()
})

describe('AppShell', () => {
  it('renders sidebar navigation, the top bar title, and the admin-only entry', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <ThemeProvider>
            <AuthProvider>
              <AppShell />
            </AuthProvider>
          </ThemeProvider>
        </ToastProvider>
      </MemoryRouter>,
    )
    expect(await screen.findByText('To-dos')).toBeInTheDocument()
    expect(screen.getByText('Admin Console')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Task Management System' })).toBeInTheDocument()
    expect(mockGetSettings).toHaveBeenCalled()
  })
})
