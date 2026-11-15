/**
 * 优先级徽标：把任务优先级映射为灰阶徽标。
 *
 * 设计契约要求不使用彩色，因此仅通过徽标描边样式与中文文案区分优先级高低：
 * 低/中 使用默认样式，高 使用描边样式，紧急 使用反色实心样式。
 */

import Badge from '../ui/Badge'
import type { TaskPriority } from '../../types/common'
import { PRIORITY_LABELS } from '../../utils/displayUtils'

/** 合法的优先级枚举值集合。 */
const VALID_PRIORITIES: readonly string[] = ['low', 'medium', 'high', 'urgent']

/** PriorityBadge 组件属性。 */
export interface PriorityBadgeProps {
  /** 优先级枚举值（后端返回字符串，未知值按“中”处理）。 */
  priority: string
}

/** 根据优先级返回徽标样式变体。 */
function resolveBadgeVariant(priority: TaskPriority): 'default' | 'outline' | 'solid' {
  if (priority === 'urgent') {
    return 'solid'
  }
  if (priority === 'high') {
    return 'outline'
  }
  return 'default'
}

/** 优先级徽标组件。 */
export default function PriorityBadge({ priority }: PriorityBadgeProps) {
  const normalizedPriority: TaskPriority = VALID_PRIORITIES.includes(priority)
    ? (priority as TaskPriority)
    : 'medium'
  return (
    <Badge variant={resolveBadgeVariant(normalizedPriority)} size="small">
      {PRIORITY_LABELS[normalizedPriority]}
    </Badge>
  )
}
