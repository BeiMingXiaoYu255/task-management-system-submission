/** 认证接口调用。 */

import type {
  AuthResponse,
  ChangePasswordPayload,
  CurrentUser,
  LoginPayload,
  RegisterPayload,
} from '../types/auth'
import type { MessageResponse } from '../types/common'
import { request } from './httpClient'

/** 登录并获取 token。 */
export function login(payload: LoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', { method: 'POST', body: payload })
}

/** 注册新用户并自动登录。 */
export function register(payload: RegisterPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/register', { method: 'POST', body: payload })
}

/** 获取当前登录用户信息与团队身份。 */
export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>('/auth/me')
}

/** 注销登录（后端加入 token 黑名单）。 */
export function logout(): Promise<MessageResponse> {
  return request<MessageResponse>('/auth/logout', { method: 'POST' })
}

/** 修改密码（统一走 /settings/password）。 */
export function changePassword(payload: ChangePasswordPayload): Promise<MessageResponse> {
  return request<MessageResponse>('/settings/password', { method: 'PUT', body: payload })
}
