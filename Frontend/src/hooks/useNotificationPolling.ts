/**
 * 通知未读数轮询 Hook：登录后每 20 秒拉取一次未读数。
 *
 * 实现要点：
 * 1. 首次加载与定时轮询共用同一请求函数，并用 inFlight 标记避免请求堆积；
 * 2. 页面隐藏时跳过定时请求，重新可见时立即补拉一次，减少无意义请求；
 * 3. 轮询失败不打断页面，只有首次/手动刷新失败才对外暴露错误文案。
 */

import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'

import { getUnreadNotificationCount } from '../api/notificationApi'
import { getErrorMessage } from './errorMessage'

/** 默认轮询间隔（20 秒）。 */
export const NOTIFICATION_POLL_INTERVAL_MS = 20_000

/** 轮询状态与操作。 */
export interface NotificationPollingState {
  /** 未读通知数（失败时保留上一次成功值）。 */
  unreadCount: number
  /** 首次加载中。 */
  loading: boolean
  /** 首次加载/手动刷新失败的中文提示。 */
  error: string | null
  /** 手动立即刷新未读数。 */
  refresh: () => Promise<void>
  /** 本地直接更新未读数（标记已读后即时反馈）。 */
  setUnreadCount: Dispatch<SetStateAction<number>>
}

/**
 * 创建通知未读数轮询状态。
 *
 * @param intervalMs 轮询间隔（毫秒），默认 20 秒
 */
export function useNotificationPolling(
  intervalMs: number = NOTIFICATION_POLL_INTERVAL_MS,
): NotificationPollingState {
  const [unreadCount, setUnreadCount] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  /** 同一时间只允许一个未读数请求在途。 */
  const inFlightRef = useRef<boolean>(false)

  /** 拉取未读数；reportError 控制失败时是否写入错误文案。 */
  const loadUnreadCount = useCallback(async (reportError: boolean): Promise<void> => {
    if (inFlightRef.current) {
      return
    }
    inFlightRef.current = true
    try {
      const unreadResult = await getUnreadNotificationCount()
      setUnreadCount(Number.isFinite(unreadResult.count) ? Math.max(0, unreadResult.count) : 0)
      setError(null)
    } catch (caughtError: unknown) {
      if (reportError) {
        setError(getErrorMessage(caughtError, 'Failed to load the unread notification count'))
      }
    } finally {
      inFlightRef.current = false
      setLoading(false)
    }
  }, [])

  /** 手动刷新：显式暴露错误。 */
  const refresh = useCallback(async (): Promise<void> => {
    await loadUnreadCount(true)
  }, [loadUnreadCount])

  useEffect(() => {
    void loadUnreadCount(true)
    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== 'hidden') {
        void loadUnreadCount(false)
      }
    }, intervalMs)
    /** 从后台切回前台时立即同步一次，避免等待下一个轮询周期。 */
    const handleVisibilityChange = (): void => {
      if (document.visibilityState === 'visible') {
        void loadUnreadCount(false)
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [intervalMs, loadUnreadCount])

  return { unreadCount, loading, error, refresh, setUnreadCount }
}
