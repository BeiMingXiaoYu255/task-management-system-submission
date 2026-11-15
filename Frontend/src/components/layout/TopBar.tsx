/**
 * 顶栏：左侧为侧边栏开关与当前页面标题，右侧为局域网地址复制、便签窗、主题切换与用户菜单。
 */

import { useState } from 'react'

import { ApiError } from '../../api/httpClient'
import { getNetworkInfo } from '../../api/systemApi'
import { useToast } from '../../context/ToastContext'
import NotificationBell from '../notification/NotificationBell'
import { copyTextToClipboard, openStickyWindow } from './environmentUtils'
import { IconCopy, IconMenu, IconSticky } from './LayoutIcons'
import ThemeToggle from './ThemeToggle'
import UserMenu from './UserMenu'
import styles from './TopBar.module.css'

/** 顶栏属性。 */
export interface TopBarProps {
  /** 当前页面标题。 */
  title: string
  /** 侧边栏是否已折叠（桌面模式）。 */
  sidebarCollapsed: boolean
  /** 是否移动端视口。 */
  isMobile: boolean
  /** 侧边栏开关回调。 */
  onToggleSidebar: () => void
}

/** 把未知异常转换为中文提示。 */
function resolveErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return fallbackMessage
}

/** 顶栏组件。 */
export function TopBar({ title, sidebarCollapsed, isMobile, onToggleSidebar }: TopBarProps) {
  const { showToast } = useToast()
  const [copyingAddress, setCopyingAddress] = useState(false)
  const toggleLabel = isMobile
    ? 'Open navigation menu'
    : sidebarCollapsed
      ? 'Expand sidebar'
      : 'Collapse sidebar'

  /** 读取局域网访问地址并复制到剪贴板。 */
  const handleCopyLanAddress = async (): Promise<void> => {
    setCopyingAddress(true)
    try {
      const networkInfo = await getNetworkInfo()
      const lanAddress = networkInfo.lanUrls[0] ?? 'http://127.0.0.1:' + networkInfo.port
      const copied = await copyTextToClipboard(lanAddress)
      if (copied) {
        showToast('LAN address copied: ' + lanAddress, 'success')
      } else {
        showToast('Copy failed. Please copy manually: ' + lanAddress, 'error')
      }
    } catch (error) {
      showToast(resolveErrorMessage(error, 'Failed to get the LAN address. Please try again later.'), 'error')
    } finally {
      setCopyingAddress(false)
    }
  }

  /** 打开便签待办小窗。 */
  const handleOpenStickyWindow = async (): Promise<void> => {
    try {
      const opened = await openStickyWindow()
      if (opened) {
        showToast('Sticky notes window opened', 'success')
      } else {
        showToast('The sticky notes window was blocked. Please allow pop-ups for this site.', 'error')
      }
    } catch (error) {
      showToast(resolveErrorMessage(error, 'Failed to open the sticky notes window'), 'error')
    }
  }

  return (
    <header className={styles.topBar}>
      <button
        type="button"
        className={styles.iconButton}
        onClick={onToggleSidebar}
        aria-label={toggleLabel}
        title={toggleLabel}
      >
        <IconMenu size={16} />
      </button>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.textButton}
          onClick={() => {
            void handleCopyLanAddress()
          }}
          disabled={copyingAddress}
          title="Copy LAN access address"
        >
          <IconCopy size={16} />
          <span className={styles.actionLabel}>LAN Address</span>
        </button>
        <button
          type="button"
          className={styles.textButton}
          onClick={() => {
            void handleOpenStickyWindow()
          }}
          title="Open sticky notes window"
        >
          <IconSticky size={16} />
          <span className={styles.actionLabel}>Sticky Notes</span>
        </button>
        <NotificationBell />
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  )
}

export default TopBar
