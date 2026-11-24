/**
 * 登录页表单校验测试：空提交与缺少密码时的错误提示。
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'
import LoginPage from '../pages/auth/LoginPage'

/** 渲染带路由与上下文 Provider 的登录页，并等待认证初始化完成。 */
async function renderLoginPage(): Promise<void> {
  render(
    <MemoryRouter>
      <ToastProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ToastProvider>
    </MemoryRouter>,
  )
  await waitFor(() => {
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
  })
}

describe('LoginPage form validation', () => {
  it('shows the username error when submitting an empty form', async () => {
    await renderLoginPage()
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    expect(screen.getByText('Please enter your username')).toBeInTheDocument()
  })

  it('shows the password error when the username has been filled in', async () => {
    await renderLoginPage()
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    expect(screen.getByText('Please enter your password')).toBeInTheDocument()
  })
})
