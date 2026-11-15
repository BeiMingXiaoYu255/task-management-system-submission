/**
 * 状态徽标：同时支持任务聚合状态与个人待办状态两套枚举。
 *
 * 两套枚举存在 inProgress / pendingReview / archived 三个重名值，中文文案一致，
 * 因此默认自动识别：命中任务独有状态时按任务展示，否则按待办展示；
 * 调用方也可通过 kind 显式指定，避免歧义。
 */

import Badge from '../ui/Badge'
import { getAssignmentStatusLabel, getTaskStatusLabel } from '../../utils/displayUtils'

/** 任务聚合状态枚举值。 */
const TASK_STATUS_VALUES: readonly string[] = ['published', 'inProgress', 'pendingReview', 'archived', 'cancelled']

/** 个人待办状态枚举值。 */
const ASSIGNMENT_STATUS_VALUES: readonly string[] = ['pendingAcceptance', 'inProgress', 'pendingReview', 'archived']

/** 状态徽标类型：任务状态或待办状态。 */
export type StatusKind = 'task' | 'assignment'

/** StatusBadge 组件属性。 */
export interface StatusBadgeProps {
  /** 状态枚举值。 */
  status: string
  /** 显式指定状态类别；缺省时自动识别。 */
  kind?: StatusKind
}

/** 判断状态值是否属于任务独有状态（用于自动识别）。 */
function isTaskOnlyStatus(status: string): boolean {
  return TASK_STATUS_VALUES.includes(status) && !ASSIGNMENT_STATUS_VALUES.includes(status)
}

/** 根据状态值返回徽标样式变体：待审核反色强调，已归档/已取消弱化。 */
function resolveBadgeVariant(status: string): 'default' | 'outline' | 'solid' {
  if (status === 'pendingReview') {
    return 'solid'
  }
  if (status === 'archived' || status === 'cancelled') {
    return 'outline'
  }
  return 'default'
}

/** 状态徽标组件。 */
export default function StatusBadge({ status, kind }: StatusBadgeProps) {
  const statusKind: StatusKind = kind ?? (isTaskOnlyStatus(status) ? 'task' : 'assignment')
  const displayLabel =
    statusKind === 'task' ? getTaskStatusLabel(status) : getAssignmentStatusLabel(status)
  return (
    <Badge variant={resolveBadgeVariant(status)} size="small">
      {displayLabel}
    </Badge>
  )
}
