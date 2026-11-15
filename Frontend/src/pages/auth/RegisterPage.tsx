/**
 * 注册页：用户名/昵称/密码/确认密码/邮箱表单，校验通过后注册并自动登录。
 * 已登录用户访问 /register 时自动跳转仪表盘。
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
  validateRegisterForm,
  type RegisterFormErrors,
} from './authFormUtils'
import styles from './RegisterPage.module.css'

/** 注册页面。 */
export default function RegisterPage() {
  const { user, loading, register } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [fieldErrors, setFieldErrors] = useState<RegisterFormErrors>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  /** 已登录用户直接进入仪表盘。 */
  useEffect(() => {
    if (!loading && user !== null) {
      navigate('/dashboard', { replace: true })
    }
  }, [loading, user, navigate])

  /** 提交注册表单。 */
  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault()
    const errors = validateRegisterForm({
      username,
      nickname,
      password,
      confirmPassword,
      email,
    })
    setFieldErrors(errors)
    setFormError('')
    if (hasFormErrors(errors)) {
      return
    }
    setSubmitting(true)
    try {
      const trimmedEmail = email.trim()
      await register({
        username: username.trim(),
        nickname: nickname.trim(),
        password,
        email: trimmedEmail ? trimmedEmail : null,
      })
      showToast('Account created. You are now signed in.', 'success')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      setFormError(resolveApiErrorMessage(error, 'Registration failed. Please check your connection and try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Sign Up"
      subtitle="Create an account to join teams, receive tasks, and publish tasks"
      footer={
        <>
          Already have an account?{' '}
          <Link className={styles.footerLink} to="/login">
            Sign In
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
          placeholder="3-30 letters, digits, or underscores"
          error={fieldErrors.username}
          autoComplete="username"
          autoFocus
        />
        <Input
          label="Nickname"
          value={nickname}
          onChange={(event) => setNickname(event.target.value)}
          placeholder="The name shown in teams"
          error={fieldErrors.nickname}
          autoComplete="nickname"
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 6 characters"
          error={fieldErrors.password}
          autoComplete="new-password"
        />
        <Input
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          placeholder="Re-enter your password"
          error={fieldErrors.confirmPassword}
          autoComplete="new-password"
        />
        <Input
          label="Email (Optional)"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Used for notifications. You can leave this blank."
          error={fieldErrors.email}
          hint="Optional, e.g. name@example.com"
          autoComplete="email"
        />
        {formError ? (
          <div className={styles.formError} role="alert">
            {formError}
          </div>
        ) : null}
        <Button htmlType="submit" block size="large" loading={submitting}>
          Sign Up
        </Button>
      </form>
    </AuthLayout>
  )
}
