/**
 * 协作模块展示工具：状态/阶段中文名、单位名称拼接与任务标签解析。
 *
 * 页面与组件统一从这里取文案，避免中文硬编码散落在各处；
 * 颜色不在此处理，全部由 CSS 变量与组件样式控制。
 */

import type { CollaborationStatus, CollaborationUnit } from '../../types/collaboration'
import type { CollaborationPhase, TaskItem } from '../../types/task'

/** 协作状态中文名。 */
export const COLLABORATION_STATUS_LABELS: Record<CollaborationStatus, string> = {
  pending: 'Pending',
  active: 'Active',
  rejected: 'Rejected',
  ended: 'Ended',
}

/** 协作任务阶段中文名。 */
export const COLLABORATION_PHASE_LABELS: Record<CollaborationPhase, string> = {
  pendingConfirmation: 'Pending Acceptance',
  executing: 'In Progress',
  targetReview: 'Receiver Review',
  sourceReview: 'Initiator Review',
  rejected: 'Rejected',
}

/** 协作任务阶段流转步骤（用于阶段条展示，不含已拒绝状态）。 */
export const COLLABORATION_PHASE_STEPS: { phase: CollaborationPhase; label: string }[] = [
  { phase: 'pendingConfirmation', label: 'Pending Acceptance' },
  { phase: 'executing', label: 'In Progress' },
  { phase: 'targetReview', label: 'Receiver Review' },
  { phase: 'sourceReview', label: 'Initiator Review' },
]

/** 子团队内我的角色中文名。 */
export const SUB_TEAM_ROLE_LABELS: Record<'admin' | 'leader' | 'member', string> = {
  admin: 'Admin',
  leader: 'Sub-team Lead',
  member: 'Member',
}

/** 安全读取协作状态中文名（后端返回未知值时回退原值）。 */
export function getCollaborationStatusLabel(status: string): string {
  return COLLABORATION_STATUS_LABELS[status as CollaborationStatus] ?? status
}

/** 安全读取协作任务阶段中文名（为空时显示“—”，未知值回退原值）。 */
export function getCollaborationPhaseLabel(phase: string | null | undefined): string {
  if (!phase) {
    return '—'
  }
  return COLLABORATION_PHASE_LABELS[phase as CollaborationPhase] ?? phase
}

/** 安全读取子团队内我的角色中文名。 */
export function getSubTeamRoleLabel(
  myRole: 'admin' | 'leader' | 'member' | null | undefined,
): string {
  if (!myRole) {
    return '—'
  }
  return SUB_TEAM_ROLE_LABELS[myRole] ?? '—'
}

/** 拼接协作单位的展示名称：优先使用后端 unitName，兼容缺失时按团队/子团队名称拼接。 */
export function formatCollaborationUnit(unit: CollaborationUnit): string {
  if (unit.unitName) {
    return unit.unitName
  }
  if (unit.subTeamName) {
    return unit.teamName + ' / ' + unit.subTeamName
  }
  return unit.teamName
}

/** 生成协作任务详情路由（协作任务统一走 /collaboration-tasks/:id）。 */
export function buildCollaborationTaskPath(taskId: number): string {
  return '/collaboration-tasks/' + String(taskId)
}

/** 任务卡片/列表展示的来源标签。 */
export interface TaskSourceTag {
  /** 标签唯一键（用于 React 列表 key）。 */
  key: string
  /** 中文文案。 */
  label: string
}

/**
 * 解析任务来源标签：协作任务、子团队任务、AI 自动分配任务。
 *
 * @param task 任务列表项
 * @returns 按固定顺序排列的标签列表（普通任务返回空数组）
 */
export function resolveTaskSourceTags(task: TaskItem): TaskSourceTag[] {
  const tags: TaskSourceTag[] = []
  if (task.collaborationId !== null) {
    const sourceName = task.sourceSubTeamName ?? task.sourceTeamName
    tags.push({
      key: 'collaboration',
      label: sourceName ? 'Collaboration - from ' + sourceName : 'Collaboration Task',
    })
  }
  if (task.subTeamId !== null) {
    tags.push({
      key: 'subTeam',
      label: task.subTeamName ? 'Sub-team - ' + task.subTeamName : 'Sub-team',
    })
  }
  if (task.autoAssigned) {
    tags.push({ key: 'autoAssigned', label: 'AI Assigned' })
  }
  return tags
}

/** 判断任务是否为协作任务。 */
export function isCollaborationTask(task: Pick<TaskItem, 'collaborationId'>): boolean {
  return task.collaborationId !== null
}