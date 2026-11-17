/**
 * 通知中心页面：分页查看通知、未读筛选、全部已读与点击跳转。
 *
 * 数据流：筛选/分页变化触发 useAsync 重新加载；单条点击由 useNotificationClick
 * 统一完成“标记已读 → 解析任务/协作目标 → 跳转”，未读筛选下已读项即时移出列表。
 */

import { useCallback, useEffect, useState } from 'react'

import { listNotifications, markAllNotificationsRead } from '../../api/notificationApi'
import AiStatusPanel from '../../components/notification/AiStatusPanel'
import NotificationList from '../../components/notification/NotificationList'
import { useNotificationClick } from '../../components/notification/useNotificationClick'
import Button from '../../components/ui/Button'
import PageHeader from '../../components/ui/PageHeader'
import Pagination from '../../components/ui/Pagination'
import Tabs from '../../components/ui/Tabs'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import type { PageResult } from '../../types/common'
import type { NotificationItem } from '../../types/notification'
import styles from './NotificationCenterPage.module.css'

/** 未读筛选键。 */
type NotificationFilterKey = 'all' | 'unread'

/** 筛选页签。 */
const FILTER_TAB_ITEMS: { key: NotificationFilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'unread', label: 'Unread' },
]

/** 通知中心页面。 */
export default function NotificationCenterPage() {
  const { showToast } = useToast()
  const [filterKey, setFilterKey] = useState<NotificationFilterKey>('all')
  const [markingAll, setMarkingAll] = useState<boolean>(false)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal, resetPage } = pagination
  const unreadOnly = filterKey === 'unread'

  /** 拉取通知分页列表。 */
  const loadNotifications = useCallback(
    () => listNotifications({ unreadOnly, page, pageSize }),
    [unreadOnly, page, pageSize],
  )

  const { data, loading, error, reload, setData } = useAsync<PageResult<NotificationItem>>(
    loadNotifications,
    [loadNotifications],
  )
  const notifications = data?.items ?? []

  /** 列表加载完成后同步总条数。 */
  useEffect(() => {
    setTotal(data?.total ?? 0)
  }, [data, setTotal])

  /** 筛选条件变化时回到第一页。 */
  useEffect(() => {
    resetPage()
  }, [unreadOnly, resetPage])

  /** 单条已读后的局部更新：未读筛选下移出列表并同步总数。 */
  const handleRead = useCallback(
    (notification: NotificationItem): void => {
      setData((previous) => {
        if (previous === null) {
          return previous
        }
        if (unreadOnly) {
          return {
            ...previous,
            items: previous.items.filter((item) => item.id !== notification.id),
            total: Math.max(0, previous.total - 1),
          }
        }
        return {
          ...previous,
          items: previous.items.map((item) =>
            item.id === notification.id ? { ...item, readFlag: true } : item,
          ),
        }
      })
    },
    [setData, unreadOnly],
  )

  const { pendingId, handleClick } = useNotificationClick({ onRead: handleRead })

  /** 全部标记已读：成功后重新拉取当前页。 */
  const handleMarkAll = async (): Promise<void> => {
    if (markingAll) {
      return
    }
    setMarkingAll(true)
    try {
      await markAllNotificationsRead()
      showToast('All notifications marked as read', 'success')
      reload()
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to mark all notifications as read. Please try again.'), 'error')
    } finally {
      setMarkingAll(false)
    }
  }

  const emptyDescription = unreadOnly
    ? 'No unread notifications. Everything has been handled.'
    : 'Task assignments, review results, and collaboration messages will appear here.'

  return (
    <div className="page-container">
      <PageHeader
        title="Notification Center"
        description="View task assignment, review result, and team collaboration notifications in one place. Click a notification to open the related task or collaboration."
        actions={
          <div className={styles.headerActions}>
            <Button
              variant="secondary"
              loading={markingAll}
              disabled={pagination.total === 0}
              onClick={() => {
                void handleMarkAll()
              }}
            >
              Mark All as Read
            </Button>
            <Button variant="secondary" onClick={reload} loading={loading}>
              Refresh
            </Button>
          </div>
        }
      />

      <div className={styles.aiStatusArea}>
        <AiStatusPanel />
      </div>

      <div className={styles.tabsArea}>
        <Tabs
          items={FILTER_TAB_ITEMS}
          activeKey={filterKey}
          onChange={(nextKey) => setFilterKey(nextKey === 'unread' ? 'unread' : 'all')}
        />
      </div>

      <section className={styles.panel}>
        <div className={styles.listArea}>
          <NotificationList
            items={notifications}
            loading={loading && notifications.length === 0}
            error={error}
            pendingId={pendingId}
            emptyTitle={unreadOnly ? 'No unread notifications' : 'No notifications yet'}
            emptyDescription={emptyDescription}
            onRetry={reload}
            onItemClick={(notification) => {
              void handleClick(notification)
            }}
          />
        </div>
      </section>

      <div className={styles.paginationArea}>
        <Pagination
          page={pagination.page}
          pageSize={pagination.pageSize}
          total={pagination.total}
          onChange={setPage}
        />
      </div>
    </div>
  )
}
