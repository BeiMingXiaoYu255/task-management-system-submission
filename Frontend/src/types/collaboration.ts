/** v1.1 团队协作与子团队类型（与后端 collaborationContract.md 对齐）。 */

import type {
  AcceptanceMode,
  DateTimeString,
  PageQuery,
  TaskPriority,
  TeamRole,
} from './common'
import type { TaskDetail, TaskItem } from './task'

/** 子团队列表项。 */
export interface SubTeamItem {
  id: number
  parentTeamId: number
  name: string
  description: string | null
  leaderUserId: number | null
  leaderNickname: string | null
  memberCount: number
  createdAt: DateTimeString
  myRole: 'admin' | 'leader' | 'member' | null
}

/** 子团队成员项。 */
export interface SubTeamMemberItem {
  userId: number
  username: string
  nickname: string
  avatar: string | null
  levelName: string
  levelOrder: number
  isLeader: boolean
}

/** 子团队详情。 */
export interface SubTeamDetail extends SubTeamItem {
  members: SubTeamMemberItem[]
}

/** 创建/修改子团队请求体。 */
export interface SaveSubTeamPayload {
  name: string
  description?: string | null
  leaderUserId?: number | null
  memberUserIds?: number[]
}

/** 协作单位（团队本级 subTeamId 为 null）。 */
export interface CollaborationUnit {
  teamId: number
  teamName: string
  subTeamId: number | null
  subTeamName: string | null
  unitName: string
}

/** 协作关系状态。 */
export type CollaborationStatus = 'pending' | 'active' | 'rejected' | 'ended'

/** 协作关系项。 */
export interface CollaborationItem {
  id: number
  initiatorUnit: CollaborationUnit
  targetUnit: CollaborationUnit
  initiatorLiaisonUserId: number | null
  initiatorLiaisonNickname: string | null
  targetLiaisonUserId: number | null
  targetLiaisonNickname: string | null
  status: CollaborationStatus
  message: string | null
  rejectComment: string | null
  createdByName: string
  createdAt: DateTimeString
  updatedAt: DateTimeString
  canConfirm: boolean
  canEnd: boolean
  canCreateTask: boolean
  myUnitRole: 'initiator' | 'target' | 'both' | null
}

/** 协作目录项。 */
export interface CollaborationDirectoryItem {
  teamId: number
  teamName: string
  description: string | null
  memberCount: number
  subTeams: {
    subTeamId: number
    name: string
    memberCount: number
    leaderNickname: string | null
  }[]
}

/** 发起协作申请请求体。 */
export interface CreateCollaborationPayload {
  initiatorTeamId: number
  initiatorSubTeamId?: number | null
  targetTeamId: number
  targetSubTeamId?: number | null
  initiatorLiaisonUserId: number
  message?: string | null
}

/** 确认协作申请请求体。 */
export interface ConfirmCollaborationPayload {
  approved: boolean
  targetLiaisonUserId?: number | null
  comment?: string | null
}

/** 协作任务（在任务字段基础上追加确认/双审核权限标记）。 */
export interface CollaborationTaskItem extends TaskItem {
  canConfirmTask: boolean
  canTargetReview: boolean
  canSourceReview: boolean
}

/** 协作任务详情。 */
export interface CollaborationTaskDetail extends TaskDetail {
  canConfirmTask: boolean
  canTargetReview: boolean
  canSourceReview: boolean
}

/** 协作任务确认请求体。 */
export interface ConfirmCollaborationTaskPayload {
  approved: boolean
  assigneeUserIds?: number[]
  comment?: string | null
}

/** 协作任务审核请求体（接收方/发起方共用）。 */
export interface ReviewCollaborationTaskPayload {
  assignmentUserId: number
  approved: boolean
  comment?: string | null
}

/** 单位候选成员（用于选择对接人/指派执行人）。 */
export interface CollaborationUnitCandidate {
  userId: number
  username: string
  nickname: string
  avatar: string | null
  levelName: string
  levelOrder: number
  role: TeamRole
}

/** 协作列表查询参数（teamId 用于团队视角过滤；后端未支持时由前端兜底过滤）。 */
export interface CollaborationQuery extends PageQuery {
  status?: CollaborationStatus
  teamId?: number
}

/** 新建协作任务请求体：仅任务基础字段，无分配对象字段（由接收方确认时指派执行人）。 */
export interface CreateCollaborationTaskPayload {
  title: string
  description?: string | null
  priority: TaskPriority
  dueAt?: string | null
  acceptanceMode: AcceptanceMode
}

/** 修改子团队请求体（接口允许只传需要修改的字段）。 */
export interface UpdateSubTeamPayload {
  name?: string
  description?: string | null
  leaderUserId?: number | null
}
