/**
 * 协作状态徽标：申请中/协作中/已拒绝/已结束统一灰度展示。
 *
 * 仅通过徽标描边样式区分类别，保持黑白灰阶设计语言。
 */

import type { CollaborationStatus } from '../../types/collaboration'
import Badge from '../ui/Badge'
import { getCollaborationStatusLabel } from './collaborationUtils'

/** 协作状态徽标属性。 */
export interface CollaborationStatusBadgeProps {
  /** 协作状态枚举值。 */
  status: string
}

/** 根据状态返回徽标样式：协作中反色强调，申请中描边，已结束/已拒绝弱化。 */
function resolveVariant(status: string): 'default' | 'outline' | 'solid' {
  if (status === 'active') {
    return 'solid'
  }
  if (status === 'pending') {
    return 'outline'
  }
  return 'default'
}

/** 协作状态徽标组件。 */
export default function CollaborationStatusBadge({ status }: CollaborationStatusBadgeProps) {
  return (
    <Badge variant={resolveVariant(status)} size="small">
      {getCollaborationStatusLabel(status)}
    </Badge>
  )
}

/** 协作状态合法值（供调用方做类型收窄时参考）。 */
export const COLLABORATION_STATUS_VALUES: readonly CollaborationStatus[] = [
  'pending',
  'active',
  'rejected',
  'ended',
]
