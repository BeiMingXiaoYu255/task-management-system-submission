/** 任务与审核相关类型。 */

import type {
  AcceptanceMode,
  AssignmentMode,
  AssignmentStatus,
  DateTimeString,
  PageQuery,
  TaskPriority,
  TaskStatus,
} from './common'

/** 任务分配（待办）项。 */
export interface TaskAssignmentItem {
  id: number
  userId: number
  username: string
  nickname: string
  avatar: string | null
  status: AssignmentStatus
  acceptedAt: DateTimeString | null
  submittedAt: DateTimeString | null
  reviewedAt: DateTimeString | null
  reviewedBy: number | null
  reviewComment: string | null
  /** v1.1 双审核阶段：target=接收方审核，source=发起方审核，普通任务为 null */
  reviewStage: 'target' | 'source' | null
  /** 接收方对接人审核时间 */
  targetReviewedAt: DateTimeString | null
  /** 接收方审核人用户主键 */
  targetReviewerId: number | null
  /** 接收方审核意见 */
  targetReviewComment: string | null
  /** 分配来源：manual 手动 / ai 自动分配 / collaboration 协作指派 */
  assignmentSource: 'manual' | 'ai' | 'collaboration'
}

/** 任务列表项。 */
export interface TaskItem {
  id: number
  teamId: number
  teamName: string
  title: string
  description: string | null
  priority: TaskPriority
  status: TaskStatus
  assignmentMode: AssignmentMode
  acceptanceMode: AcceptanceMode
  targetLevelMin: number | null
  targetLevelMax: number | null
  dueAt: DateTimeString | null
  createdBy: number | null
  createdByName: string
  createdAt: DateTimeString
  updatedAt: DateTimeString
  archivedAt: DateTimeString | null
  assignments: TaskAssignmentItem[]
  myAssignment: TaskAssignmentItem | null
  canReview: boolean
  canEdit: boolean
  /** 无执行人且当前用户可手动指派 */
  canAssign: boolean
  reviewCount: number
  // ===== v1.1 子团队 / 协作 / AI 扩展字段 =====
  subTeamId: number | null
  subTeamName: string | null
  sourceTeamId: number | null
  sourceTeamName: string | null
  sourceSubTeamId: number | null
  sourceSubTeamName: string | null
  targetTeamId: number | null
  targetTeamName: string | null
  targetSubTeamId: number | null
  targetSubTeamName: string | null
  collaborationId: number | null
  collaborationPhase: CollaborationPhase | null
  collaborationComment: string | null
  autoAssigned: boolean
  requiredSkillNames: string[]
}

/** 协作任务阶段。 */
export type CollaborationPhase =
  | 'pendingConfirmation'
  | 'executing'
  | 'targetReview'
  | 'sourceReview'
  | 'rejected'

/** 审核记录。 */
export interface ReviewRecord {
  id: number
  taskId: number
  assignmentId: number
  reviewerId: number
  reviewerName: string
  result: 'approved' | 'rejected'
  comment: string | null
  createdAt: DateTimeString
}

/** 任务详情。 */
export interface TaskDetail extends TaskItem {
  reviews: ReviewRecord[]
}

/** 创建任务请求体。 */
export interface CreateTaskPayload {
  title: string
  description?: string | null
  priority: TaskPriority
  dueAt?: string | null
  assignmentMode: AssignmentMode
  acceptanceMode: AcceptanceMode
  targetUserIds?: number[]
  targetLevelMin?: number
  targetLevelMax?: number
  /** v1.1 任务所属子团队（可选） */
  subTeamId?: number | null
  /** v1.1 是否由 AI 自动分配执行人 */
  autoAssign?: boolean
  /** v1.1 AI 自动分配所需技能标签 */
  requiredSkillNames?: string[]
}

/** 修改任务请求体。 */
export interface UpdateTaskPayload {
  title?: string
  description?: string | null
  priority?: TaskPriority
  dueAt?: string | null
  acceptanceMode?: AcceptanceMode
}

/** 任务列表查询参数。 */
export interface TaskQuery extends PageQuery {
  status?: string
  priority?: string
  keyword?: string
  createdBy?: number
  assigneeId?: number
  sortBy?: 'createdAt' | 'dueAt' | 'priority'
  sortOrder?: 'asc' | 'desc'
}

/** 审核请求体。 */
export interface ReviewTaskPayload {
  assignmentUserId: number
  approved: boolean
  comment?: string | null
}

/** 我参与/发布的任务查询参数。 */
export interface MyTaskQuery extends TaskQuery {
  role?: 'created' | 'assigned'
  teamId?: number
}

/** 手动指派执行人请求体（为无执行人的任务补派成员）。 */
export interface AssignTaskMembersPayload {
  userIds: number[]
}
