/**
 * 通知列表：铃铛下拉（compact）与通知中心（完整）共用。
 *
 * 展示通知类型、标题、内容摘要、相对时间与跳转提示，
 * 并覆盖加载中、加载失败、空列表三种状态；未读通知用左侧竖线与字重区分。
 */

import type { NotificationItem } from '../../types/notification'
import { formatRelativeTime } from '../../utils/formatUtils'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import { getNotificationTargetHint, getNotificationTypeLabel } from './notificationUtils'
import styles from './NotificationList.module.css'

/** 通知列表属性。 */
export interface NotificationListProps {
  /** 通知列表。 */
  items: NotificationItem[]
  /** 是否使用紧凑样式（下拉面板）。 */
  compact?: boolean
  /** 是否加载中。 */
  loading?: boolean
  /** 加载失败的中文提示。 */
  error?: string | null
  /** 正在跳转的通知 ID。 */
  pendingId?: number | null
  /** 空状态标题。 */
  emptyTitle?: string
  /** 空状态说明。 */
  emptyDescription?: string
  /** 重试回调。 */
  onRetry?: () => void
  /** 点击通知回调。 */
  onItemClick: (notification: NotificationItem) => void
}

/** 通知列表组件。 */
export default function NotificationList({
  items,
  compact = false,
  loading = false,
  error = null,
  pendingId = null,
  emptyTitle = 'No notifications yet',
  emptyDescription,
  onRetry,
  onItemClick,
}: NotificationListProps) {
  if (loading) {
    return (
      <div className={styles.stateBox}>
        <Spinner size="small" />
        <span className={styles.stateText}>Loading notifications...</span>
      </div>
    )
  }

  if (error !== null) {
    return (
      <div className={styles.errorBox}>
        <p className={styles.errorText}>{error}</p>
        {onRetry ? (
          <Button variant="secondary" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : null}
      </div>
    )
  }

  if (items.length === 0) {
    if (compact) {
      return (
        <div className={styles.compactEmpty}>
          <p className={styles.compactEmptyTitle}>{emptyTitle}</p>
          {emptyDescription ? (
            <p className={styles.stateText}>{emptyDescription}</p>
          ) : null}
        </div>
      )
    }
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <ul className={compact ? styles.list + ' ' + styles.compactList : styles.list}>
      {items.map((notification) => {
        const isPending = pendingId === notification.id
        const itemClassName = notification.readFlag
          ? styles.item
          : styles.item + ' ' + styles.unreadItem
        return (
          <li key={notification.id}>
            <button
              type="button"
              className={itemClassName}
              disabled={isPending}
              aria-busy={isPending || undefined}
              onClick={() => onItemClick(notification)}
            >
              <span className={styles.itemHeader}>
                <span className={styles.typeLabel}>{getNotificationTypeLabel(notification.type)}</span>
                <span className={styles.timeText}>{formatRelativeTime(notification.createdAt)}</span>
              </span>
              <span className={styles.titleRow}>
                {notification.readFlag ? null : (
                  <span className={styles.unreadDot} aria-hidden="true" />
                )}
                <span className={styles.title}>{notification.title}</span>
              </span>
              {notification.content ? (
                <span className={styles.content}>{notification.content}</span>
              ) : null}
              <span className={styles.targetHint}>
                {isPending ? 'Opening...' : getNotificationTargetHint(notification)}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
