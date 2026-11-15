/**
 * 登录页：用户名 + 密码表单，前端先做字段校验，提交成功后跳转 /dashboard。
 * 已登录用户访问 /login 时自动跳转仪表盘。
 */

import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import AuthLayout from '../../components/layout/AuthLayout'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import {
  hasFormErrors,
  resolveApiErrorMessage,
  validateLoginForm,
  type LoginFormErrors,
} from './authFormUtils'
import styles from './LoginPage.module.css'

/** 登录页面。 */
export default function LoginPage() {
  const { user, loading, login } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<LoginFormErrors>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  /** 已登录用户直接进入仪表盘。 */
  useEffect(() => {
    if (!loading && user !== null) {
      navigate('/dashboard', { replace: true })
    }
  }, [loading, user, navigate])

  /** 提交登录表单。 */
  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault()
    const errors = validateLoginForm(username, password)
    setFieldErrors(errors)
    setFormError('')
    if (hasFormErrors(errors)) {
      return
    }
    setSubmitting(true)
    try {
      await login({ username: username.trim(), password })
      showToast('Signed in successfully', 'success')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      setFormError(resolveApiErrorMessage(error, 'Sign-in failed. Please check your connection and try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Sign In"
      subtitle="Sign in with your username and password"
      footer={
        <>
          Don't have an account?{' '}
          <Link className={styles.footerLink} to="/register">
            Sign Up
          </Link>
        </>
      }
    >
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          void handleSubmit(event)
        }}
      >
        <Input
          label="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="Enter your username"
          error={fieldErrors.username}
          autoComplete="username"
          autoFocus
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter your password"
          error={fieldErrors.password}
          autoComplete="current-password"
        />
        {formError ? (
          <div className={styles.formError} role="alert">
            {formError}
          </div>
        ) : null}
        <Button htmlType="submit" block size="large" loading={submitting}>
          Sign In
        </Button>
      </form>
    </AuthLayout>
  )
}
