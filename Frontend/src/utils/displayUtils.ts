/** 枚举显示映射：所有中文文案集中维护，避免页面重复硬编码。 */

import type {
  AssignmentStatus,
  GlobalRole,
  JoinMethod,
  TaskPriority,
  TaskStatus,
  TeamRole,
  TeamStatus,
} from '../types/common'

/** 优先级中文名。 */
export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  urgent: 'Urgent',
}

/** 优先级排序权重（越大越优先）。 */
export const PRIORITY_WEIGHTS: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  urgent: 4,
}

/** 任务状态中文名。 */
export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  published: 'Published',
  inProgress: 'In Progress',
  pendingReview: 'Pending Review',
  archived: 'Archived',
  cancelled: 'Cancelled',
}

/** 待办状态中文名。 */
export const ASSIGNMENT_STATUS_LABELS: Record<AssignmentStatus, string> = {
  pendingAcceptance: 'Pending Acceptance',
  inProgress: 'In Progress',
  pendingReview: 'Pending Review',
  archived: 'Archived',
}

/** 团队角色中文名。 */
export const TEAM_ROLE_LABELS: Record<TeamRole, string> = {
  admin: 'Team Admin',
  subAdmin: 'Sub-admin',
  member: 'Member',
}

/** 全局角色中文名。 */
export const GLOBAL_ROLE_LABELS: Record<GlobalRole, string> = {
  superAdmin: 'Super Admin',
  globalAdmin: 'Global Admin',
  user: 'Standard User',
}

/** 团队加入方式中文名。 */
export const JOIN_METHOD_LABELS: Record<JoinMethod, string> = {
  free: 'Free Join',
  approval: 'Approval Required',
  inviteOnly: 'Invite Code',
}

/** 团队认证状态中文名。 */
export const TEAM_STATUS_LABELS: Record<TeamStatus, string> = {
  pending: 'Pending',
  active: 'Certified',
  rejected: 'Rejected',
}

/** 安全读取优先级中文名（后端返回未知值时回退原值）。 */
export function getPriorityLabel(priority: string): string {
  return PRIORITY_LABELS[priority as TaskPriority] ?? priority
}

/** 安全读取任务状态中文名。 */
export function getTaskStatusLabel(status: string): string {
  return TASK_STATUS_LABELS[status as TaskStatus] ?? status
}

/** 安全读取待办状态中文名。 */
export function getAssignmentStatusLabel(status: string): string {
  return ASSIGNMENT_STATUS_LABELS[status as AssignmentStatus] ?? status
}

/** 获取姓名首字符作为头像占位文本。 */
export function getInitials(name: string | null | undefined): string {
  if (!name) {
    return '?'
  }
  return name.trim().slice(0, 1).toUpperCase()
}
