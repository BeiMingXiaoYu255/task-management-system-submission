/** 站内通知类型。 */

/** 通知项。 */
export interface NotificationItem {
  id: number
  type: string
  title: string
  content: string | null
  taskId: number | null
  collaborationId: number | null
  readFlag: boolean
  createdAt: string
}

/** 未读数。 */
export interface UnreadCount {
  count: number
}

/** 通知查询参数。 */
export interface NotificationQuery {
  unreadOnly?: boolean
  page?: number
  pageSize?: number
}
