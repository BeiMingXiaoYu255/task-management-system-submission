/** 待办清单类型。 */

import type { DateTimeString, PageQuery } from './common'

/** 待办列表项。 */
export interface TodoItem {
  assignmentId: number
  taskId: number
  teamId: number
  teamName: string
  title: string
  description: string | null
  priority: string
  taskStatus: string
  assignmentStatus: string
  dueAt: DateTimeString | null
  createdByName: string
  acceptedAt: DateTimeString | null
  createdAt: DateTimeString
  overdue: boolean
  // ===== v1.1 协作扩展 =====
  collaborationId: number | null
  collaborationPhase: string | null
  sourceTeamName: string | null
  targetTeamName: string | null
  reviewStage: 'target' | 'source' | null
}

/** 待办统计。 */
export interface TodoStats {
  total: number
  pendingAcceptance: number
  inProgress: number
  pendingReview: number
  archived: number
  overdue: number
}

/** 待办查询参数。 */
export interface TodoQuery extends PageQuery {
  status?: string
  priority?: string
  teamId?: number
  keyword?: string
  sortBy?: 'priority' | 'dueAt' | 'createdAt'
  sortOrder?: 'asc' | 'desc'
  includeArchived?: boolean
}
