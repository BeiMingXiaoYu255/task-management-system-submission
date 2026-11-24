/**
 * 通知下拉面板：展示最近 5 条通知，支持单条已读跳转、全部已读与进入通知中心。
 */

import { useCallback, useState, type Dispatch, type SetStateAction } from 'react'
import { useNavigate } from 'react-router-dom'

import { listNotifications, markAllNotificationsRead } from '../../api/notificationApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { PageResult } from '../../types/common'
import type { NotificationItem } from '../../types/notification'
import Button from '../ui/Button'
import NotificationList from './NotificationList'
import { useNotificationClick } from './useNotificationClick'
import styles from './NotificationDropdown.module.css'

/** 下拉面板展示的通知条数。 */
const RECENT_NOTIFICATION_SIZE = 5

/** 通知下拉面板属性。 */
export interface NotificationDropdownProps {
  /** 关闭面板。 */
  onClose: () => void
  /** 当前未读数（用于“全部已读”禁用态与标题）。 */
  unreadCount: number
  /** 未读数变更回调。 */
  onUnreadCountChange: Dispatch<SetStateAction<number>>
}

/** 通知下拉面板。 */
export default function NotificationDropdown({
  onClose,
  unreadCount,
  onUnreadCountChange,
}: NotificationDropdownProps) {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [markingAll, setMarkingAll] = useState<boolean>(false)

  /** 面板挂载时拉取最近通知；打开即刷新，保证消息较新。 */
  const { data, loading, error, reload, setData } = useAsync<PageResult<NotificationItem>>(
    () => listNotifications({ page: 1, pageSize: RECENT_NOTIFICATION_SIZE }),
    [],
  )
  const notifications = data?.items ?? []

  /** 单条已读：局部更新列表并同步未读数。 */
  const handleRead = useCallback(
    (notification: NotificationItem): void => {
      setData((previous) => {
        if (previous === null) {
          return previous
        }
        return {
          ...previous,
          items: previous.items.map((item) =>
            item.id === notification.id ? { ...item, readFlag: true } : item,
          ),
        }
      })
      onUnreadCountChange((previousCount) => Math.max(0, previousCount - 1))
    },
    [onUnreadCountChange, setData],
  )

  const { pendingId, handleClick } = useNotificationClick({ onRead: handleRead, onNavigated: onClose })

  /** 全部标记已读：成功后同步本地列表与未读数。 */
  const handleMarkAll = async (): Promise<void> => {
    if (markingAll || unreadCount === 0) {
      return
    }
    setMarkingAll(true)
    try {
      await markAllNotificationsRead()
      setData((previous) => {
        if (previous === null) {
          return previous
        }
        return {
          ...previous,
          items: previous.items.map((item) => ({ ...item, readFlag: true })),
        }
      })
      onUnreadCountChange(0)
      showToast('All notifications marked as read', 'success')
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to mark all notifications as read. Please try again.'), 'error')
    } finally {
      setMarkingAll(false)
    }
  }

  /** 进入通知中心。 */
  const handleViewAll = (): void => {
    onClose()
    navigate('/notifications')
  }

  return (
    <div className={styles.dropdown} role="dialog" aria-label="Notifications panel">
      <header className={styles.header}>
        <span className={styles.headerTitle}>
          Notifications{unreadCount > 0 ? ' (' + String(unreadCount) + ' unread)' : ''}
        </span>
        <Button
          variant="ghost"
          size="small"
          loading={markingAll}
          disabled={unreadCount === 0}
          onClick={() => {
            void handleMarkAll()
          }}
        >
          Mark All as Read
        </Button>
      </header>
      <div className={styles.body}>
        <NotificationList
          items={notifications}
          compact
          loading={loading}
          error={error}
          pendingId={pendingId}
          emptyTitle="No notifications yet"
          emptyDescription="New task and collaboration messages will appear here."
          onRetry={reload}
          onItemClick={(notification) => {
            void handleClick(notification)
          }}
        />
      </div>
      <footer className={styles.footer}>
        <Button variant="ghost" size="small" block onClick={handleViewAll}>
          View All Notifications
        </Button>
      </footer>
    </div>
  )
}
