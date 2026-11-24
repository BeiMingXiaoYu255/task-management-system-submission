/**
 * 通知展示与跳转工具：统一类型文案、目标提示与点击路由解析。
 *
 * 路由规则：
 * - 协作任务类通知 → /collaboration-tasks/{taskId}；
 * - 普通任务通知 → 通知未携带团队 ID，先查询任务详情获得 teamId，再进入
 *   /teams/{teamId}/tasks/{taskId}，查询失败回退任务中心 /tasks；
 * - 协作关系通知 → /collaborations/{collaborationId}。
 */

import { getTask } from '../../api/taskApi'
import type { NotificationItem } from '../../types/notification'

/** 通知类型 → 中文短标签。 */
const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  collaborationApplied: 'Collaboration Request',
  collaborationConfirmed: 'Collaboration Confirmed',
  collaborationRejected: 'Collaboration Rejected',
  collaborationEnded: 'Collaboration Ended',
  collaborationTaskReceived: 'Collaboration Task',
  collaborationTaskConfirmed: 'Collaboration Task Confirmed',
  collaborationTaskRejected: 'Collaboration Task Rejected',
  collaborationTaskTargetReview: 'Collaboration Task Review',
  collaborationTaskSourceReview: 'Collaboration Task Final Review',
  collaborationTaskArchived: 'Collaboration Task Archived',
  taskAutoAssigned: 'AI Auto-assignment',
  taskMatchReminder: 'Task Match Reminder',
  taskAssignFailed: 'Auto-assignment Unmatched',
  taskReviewResult: 'Task Review Result',
  taskAssigned: 'Task Assigned',
}

/** 获取通知类型中文标签，未知类型回退为“通知”。 */
export function getNotificationTypeLabel(type: string): string {
  return NOTIFICATION_TYPE_LABELS[type] ?? 'Notification'
}

/** 判断是否为协作任务类通知。 */
export function isCollaborationTaskNotification(notification: NotificationItem): boolean {
  return notification.collaborationId !== null || notification.type.startsWith('collaborationTask')
}

/** 拼接普通任务详情路由。 */
export function buildTaskDetailPath(teamId: number, taskId: number): string {
  return '/teams/' + String(teamId) + '/tasks/' + String(taskId)
}

/** 通知卡片右侧的目标提示文案。 */
export function getNotificationTargetHint(notification: NotificationItem): string {
  if (notification.taskId !== null) {
    return isCollaborationTaskNotification(notification) ? 'View collaboration task →' : 'View task details →'
  }
  if (notification.collaborationId !== null) {
    return 'View collaboration details →'
  }
  return ''
}

/** 解析无需额外请求即可确定的路由；返回 null 表示仍需按任务查询。 */
function resolveImmediatePath(notification: NotificationItem): string | null {
  if (notification.taskId !== null && isCollaborationTaskNotification(notification)) {
    return '/collaboration-tasks/' + String(notification.taskId)
  }
  if (notification.taskId === null && notification.collaborationId !== null) {
    return '/collaborations/' + String(notification.collaborationId)
  }
  return null
}

/**
 * 解析通知点击目标路由。
 *
 * @returns 目标路由；通知没有关联目标时返回 null
 */
export async function resolveNotificationPath(
  notification: NotificationItem,
): Promise<string | null> {
  const immediatePath = resolveImmediatePath(notification)
  if (immediatePath !== null) {
    return immediatePath
  }
  if (notification.taskId === null) {
    return null
  }
  try {
    const task = await getTask(notification.taskId)
    // 部分协作任务通知只带 taskId，需查询任务详情判断是否属于协作任务
    if (task.collaborationId !== null) {
      return '/collaboration-tasks/' + String(task.id)
    }
    return buildTaskDetailPath(task.teamId, task.id)
  } catch {
    // 任务不存在或无权访问时回退任务中心，避免点击无反馈
    return '/tasks'
  }
}
