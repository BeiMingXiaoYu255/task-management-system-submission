/**
 * 认证表单校验与错误文案处理：登录/注册页共用，保证错误提示风格一致。
 */

import { ApiError } from '../../api/httpClient'

/** 用户名规则：3-30 位字母、数字或下划线（与数据库契约一致）。 */
const USERNAME_PATTERN = /^[A-Za-z0-9_]{3,30}$/

/** 邮箱格式规则（仅做基础格式校验）。 */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** 密码最小长度。 */
const PASSWORD_MIN_LENGTH = 6

/** 密码最大长度。 */
const PASSWORD_MAX_LENGTH = 64

/** 登录表单错误。 */
export interface LoginFormErrors {
  /** 用户名错误。 */
  username?: string
  /** 密码错误。 */
  password?: string
}

/** 注册表单字段值。 */
export interface RegisterFormValues {
  /** 用户名。 */
  username: string
  /** 昵称。 */
  nickname: string
  /** 密码。 */
  password: string
  /** 确认密码。 */
  confirmPassword: string
  /** 邮箱（可空）。 */
  email: string
}

/** 注册表单错误。 */
export interface RegisterFormErrors {
  /** 用户名错误。 */
  username?: string
  /** 昵称错误。 */
  nickname?: string
  /** 密码错误。 */
  password?: string
  /** 确认密码错误。 */
  confirmPassword?: string
  /** 邮箱错误。 */
  email?: string
}

/** 校验登录表单，返回字段级中文错误。 */
export function validateLoginForm(username: string, password: string): LoginFormErrors {
  const errors: LoginFormErrors = {}
  const trimmedUsername = username.trim()
  if (!trimmedUsername) {
    errors.username = 'Please enter your username'
  } else if (!USERNAME_PATTERN.test(trimmedUsername)) {
    errors.username = 'Username must be 3-30 letters, digits, or underscores'
  }
  if (!password) {
    errors.password = 'Please enter your password'
  } else if (password.length < PASSWORD_MIN_LENGTH) {
    errors.password = 'Password must be at least ' + PASSWORD_MIN_LENGTH + ' characters'
  } else if (password.length > PASSWORD_MAX_LENGTH) {
    errors.password = 'Password must be at most ' + PASSWORD_MAX_LENGTH + ' characters'
  }
  return errors
}

/** 校验注册表单，返回字段级中文错误。 */
export function validateRegisterForm(values: RegisterFormValues): RegisterFormErrors {
  const errors: RegisterFormErrors = {}
  const trimmedUsername = values.username.trim()
  if (!trimmedUsername) {
    errors.username = 'Please enter your username'
  } else if (!USERNAME_PATTERN.test(trimmedUsername)) {
    errors.username = 'Username must be 3-30 letters, digits, or underscores'
  }

  const trimmedNickname = values.nickname.trim()
  if (!trimmedNickname) {
    errors.nickname = 'Please enter your nickname'
  } else if (trimmedNickname.length > 50) {
    errors.nickname = 'Nickname must be at most 50 characters'
  }

  if (!values.password) {
    errors.password = 'Please enter your password'
  } else if (values.password.length < PASSWORD_MIN_LENGTH) {
    errors.password = 'Password must be at least ' + PASSWORD_MIN_LENGTH + ' characters'
  } else if (values.password.length > PASSWORD_MAX_LENGTH) {
    errors.password = 'Password must be at most ' + PASSWORD_MAX_LENGTH + ' characters'
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = 'Please re-enter your password'
  } else if (values.confirmPassword !== values.password) {
    errors.confirmPassword = 'The passwords do not match'
  }

  const trimmedEmail = values.email.trim()
  if (trimmedEmail && !EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = 'Invalid email format'
  }
  return errors
}

/** 判断错误对象是否包含任意字段错误。 */
export function hasFormErrors(errors: object): boolean {
  return Object.keys(errors).length > 0
}

/** 把接口异常转换为中文提示：优先使用后端返回的中文 message。 */
export function resolveApiErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return fallbackMessage
}
