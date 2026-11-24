/**
 * 通知铃铛：顶栏入口，轮询未读数并展开最近通知下拉面板。
 *
 * 未读数每 20 秒轮询（页面隐藏时暂停），点击铃铛加载最近 5 条通知；
 * 支持点击外部/Esc 关闭、全部已读与进入通知中心。
 */

import { useEffect, useRef, useState } from 'react'

import { useNotificationPolling } from '../../hooks/useNotificationPolling'
import NotificationDropdown from './NotificationDropdown'
import styles from './NotificationBell.module.css'

/** 铃铛内联图标（不引入图标库）。 */
function BellIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8.5C6 5.8 7.8 4 10 4C12.2 4 14 5.8 14 8.5V12L15.5 14H4.5L6 12V8.5Z" />
      <path d="M8.2 16C8.5 16.8 9.2 17.2 10 17.2C10.8 17.2 11.5 16.8 11.8 16" />
    </svg>
  )
}

/** 通知铃铛组件。 */
export default function NotificationBell() {
  const [open, setOpen] = useState<boolean>(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { unreadCount, loading, error, setUnreadCount } = useNotificationPolling()

  useEffect(() => {
    if (!open) {
      return
    }
    /** 点击面板外部时关闭。 */
    const handleMouseDown = (event: MouseEvent): void => {
      if (containerRef.current !== null && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    /** Esc 关闭面板。 */
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const badgeText = unreadCount > 99 ? '99+' : String(unreadCount)
  const ariaLabel = loading
    ? 'Loading notifications'
    : error !== null
      ? 'Notifications. Failed to load the unread count; retrying automatically.'
      : 'Notifications, ' + String(unreadCount) + ' unread'

  return (
    <div className={styles.wrapper} ref={containerRef}>
      <button
        type="button"
        className={styles.bellButton}
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={open}
        title={ariaLabel}
        onClick={() => setOpen((previous) => !previous)}
      >
        <BellIcon />
        {unreadCount > 0 ? <span className={styles.badge}>{badgeText}</span> : null}
        {error !== null && unreadCount === 0 ? (
          <span className={styles.errorDot} aria-hidden="true" />
        ) : null}
      </button>
      {open ? (
        <NotificationDropdown
          onClose={() => setOpen(false)}
          unreadCount={unreadCount}
          onUnreadCountChange={setUnreadCount}
        />
      ) : null}
    </div>
  )
}
