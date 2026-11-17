/** 站内通知接口调用（v1.1 协作与 AI 通知共用）。 */

import type { MessageResponse, PageResult } from '../types/common'
import type { NotificationItem, NotificationQuery, UnreadCount } from '../types/notification'
import { request } from './httpClient'

/** 当前用户通知分页列表（时间倒序）。 */
export function listNotifications(
  query: NotificationQuery = {},
): Promise<PageResult<NotificationItem>> {
  return request<PageResult<NotificationItem>>('/notifications', {
    query: {
      // 仅在未读筛选时显式传 true，避免部分实现把 false 字符串误判为开启筛选
      unreadOnly: query.unreadOnly === true ? true : undefined,
      page: query.page,
      pageSize: query.pageSize,
    },
  })
}

/** 当前用户未读通知数。 */
export function getUnreadNotificationCount(): Promise<UnreadCount> {
  return request<UnreadCount>('/notifications/unread-count')
}

/** 标记单条通知已读（仅本人），返回更新后的通知。 */
export function markNotificationRead(notificationId: number): Promise<NotificationItem> {
  return request<NotificationItem>('/notifications/' + notificationId + '/read', { method: 'PUT' })
}

/** 标记全部通知已读。 */
export function markAllNotificationsRead(): Promise<MessageResponse> {
  return request<MessageResponse>('/notifications/read-all', { method: 'PUT' })
}
