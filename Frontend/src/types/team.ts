/** 团队相关类型。 */

import type {
  DateTimeString,
  JoinMethod,
  TeamRole,
  TeamStatus,
} from './common'
import type { SkillItem } from './user'

/** 团队列表项。 */
export interface TeamBrief {
  id: number
  name: string
  description: string | null
  status: TeamStatus
  joinMethod: JoinMethod
  createdBy: number | null
  memberCount: number
  createdAt: DateTimeString
}

/** 团队级别。 */
export interface TeamLevel {
  id: number
  teamId: number
  name: string
  levelOrder: number
  canCreateTask: boolean
  memberCount: number
}

/** 团队成员列表项。 */
export interface TeamMemberItem {
  id: number
  userId: number
  username: string
  nickname: string
  avatar: string | null
  role: TeamRole
  levelId: number
  levelName: string
  levelOrder: number
  joinedAt: DateTimeString
  skills: SkillItem[]
}

/** 团队详情。 */
export interface TeamDetail extends TeamBrief {
  inviteCode: string | null
  inviteExpiresAt: DateTimeString | null
  levels: TeamLevel[]
  members: TeamMemberItem[]
  currentUserRole: TeamRole
  currentUserLevelOrder: number
}

/** 创建团队请求体。 */
export interface CreateTeamPayload {
  name: string
  description?: string | null
  joinMethod: JoinMethod
}

/** 修改团队请求体。 */
export interface UpdateTeamPayload {
  name?: string
  description?: string | null
  joinMethod?: JoinMethod
}

/** 加入团队请求体。 */
export interface JoinTeamPayload {
  teamId?: number
  inviteCode?: string
  message?: string
}

/** 加入团队结果。 */
export interface JoinTeamResult {
  status: 'joined' | 'pending'
  teamId: number
  teamName: string
  message: string
}

/** 入团申请项。 */
export interface JoinRequestItem {
  id: number
  teamId: number
  userId: number
  username: string
  nickname: string
  message: string | null
  status: 'pending' | 'approved' | 'rejected'
  createdAt: DateTimeString
}

/** 新建/修改级别请求体。 */
export interface SaveLevelPayload {
  name: string
  levelOrder: number
  canCreateTask: boolean
}

/** 生成邀请码请求体。 */
export interface GenerateInviteCodePayload {
  expiresInHours?: number
  maxUses?: number
}

/** 任务可选成员候选项。 */
export interface MemberCandidateItem {
  userId: number
  username: string
  nickname: string
  avatar: string | null
  role: TeamRole
  levelId: number
  levelName: string
  levelOrder: number
  skills: SkillItem[]
}
