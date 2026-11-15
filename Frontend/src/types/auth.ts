/** 认证与当前用户类型。 */

import type { TeamRole, TeamStatus, DateTimeString } from './common'
import type { UserDetail } from './user'

/** 当前用户在某团队中的身份。 */
export interface TeamMembership {
  teamId: number
  teamName: string
  teamStatus: TeamStatus
  role: TeamRole
  levelId: number
  levelName: string
  levelOrder: number
  canCreateTask: boolean
  joinedAt: DateTimeString
}

/** 当前用户信息（用户资料 + 团队身份列表）。 */
export interface CurrentUser {
  user: UserDetail
  teams: TeamMembership[]
}

/** 登录请求体。 */
export interface LoginPayload {
  username: string
  password: string
}

/** 注册请求体。 */
export interface RegisterPayload {
  username: string
  password: string
  nickname: string
  email?: string | null
}

/** 登录/注册响应。 */
export interface AuthResponse {
  token: string
  user: CurrentUser
}

/** 修改密码请求体。 */
export interface ChangePasswordPayload {
  oldPassword: string
  newPassword: string
}

/** 注销账号请求体。 */
export interface DeleteAccountPayload {
  password: string
}
