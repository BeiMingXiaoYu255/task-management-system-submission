/**
 * 通知点击 Hook：统一处理“标记已读 → 解析目标 → 跳转”流程。
 *
 * 标记已读失败不阻塞跳转（只提示），避免用户因一次失败无法查看任务；
 * 跳转过程中暴露 pendingId 供列表禁用重复点击并展示“跳转中”。
 */

import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { markNotificationRead } from '../../api/notificationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { NotificationItem } from '../../types/notification'
import { resolveNotificationPath } from './notificationUtils'

/** 点击行为配置。 */
export interface NotificationClickOptions {
  /** 单条通知成功标记已读后的回调（用于局部更新列表与未读数）。 */
  onRead: (notification: NotificationItem) => void
  /** 跳转完成后的回调（下拉面板据此关闭）。 */
  onNavigated?: () => void
}

/** 点击行为状态。 */
export interface NotificationClickState {
  /** 正在跳转的通知 ID；无跳转时为 null。 */
  pendingId: number | null
  /** 处理单条通知点击。 */
  handleClick: (notification: NotificationItem) => Promise<void>
}

/**
 * 创建通知点击处理器。
 *
 * @param options 已读回调与跳转完成回调
 */
export function useNotificationClick(options: NotificationClickOptions): NotificationClickState {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [pendingId, setPendingId] = useState<number | null>(null)
  const onRead = options.onRead
  const onNavigated = options.onNavigated

  const handleClick = useCallback(
    async (notification: NotificationItem): Promise<void> => {
      setPendingId(notification.id)
      try {
        if (!notification.readFlag) {
          try {
            await markNotificationRead(notification.id)
            onRead(notification)
          } catch (caughtError: unknown) {
            showToast(getErrorMessage(caughtError, 'Failed to mark the notification as read'), 'error')
          }
        }
        const targetPath = await resolveNotificationPath(notification)
        if (targetPath === null) {
          return
        }
        navigate(targetPath)
        if (onNavigated) {
          onNavigated()
        }
      } catch (caughtError: unknown) {
        showToast(getErrorMessage(caughtError, 'Failed to open the notification. Please try again.'), 'error')
      } finally {
        setPendingId(null)
      }
    },
    [navigate, onNavigated, onRead, showToast],
  )

  return { pendingId, handleClick }
}
