/**
 * 应用外壳：左侧可折叠导航 + 顶部工具栏 + 内容区（最大宽 1200px）。
 * - 挂载时拉取服务端界面设置并应用（主题/字号/字体）；
 * - ≤900px 时侧边栏切换为抽屉形态；
 * - 内容区通过 <Outlet /> 渲染当前路由页面。
 */

import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { getSettings } from '../../api/settingApi'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { resolvePageTitle } from './navigationConfig'
import { useMediaQuery } from './useMediaQuery'
import styles from './AppShell.module.css'

/** 侧边栏折叠状态在 localStorage 中的键名。 */
const SIDEBAR_STORAGE_KEY = 'tms.sidebarCollapsed'

/** 读取本地保存的侧边栏折叠状态。 */
function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

/** 应用外壳组件。 */
export default function AppShell() {
  const { user } = useAuth()
  const { applyUserSettings } = useTheme()
  const location = useLocation()
  const isMobile = useMediaQuery('(max-width: 900px)')
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(readSidebarCollapsed)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const effectiveCollapsed = isMobile ? false : sidebarCollapsed

  /** 登录后加载服务端界面设置并应用：失败时保留本地缓存主题，不阻塞界面。 */
  useEffect(() => {
    let disposed = false
    const loadUserSettings = async (): Promise<void> => {
      try {
        const userSettings = await getSettings()
        if (!disposed) {
          applyUserSettings(userSettings)
        }
      } catch {
        // 读取设置失败（如接口暂不可用）时静默回退到本地缓存设置
      }
    }
    void loadUserSettings()
    return () => {
      disposed = true
    }
  }, [applyUserSettings, user?.user.id])

  /** 路由变化时自动关闭移动端抽屉。 */
  useEffect(() => {
    setMobileSidebarOpen(false)
  }, [location.pathname])

  /** 视口变宽（离开移动端断点）时自动关闭抽屉，避免再次缩窄时抽屉意外保持展开。 */
  useEffect(() => {
    if (!isMobile) {
      setMobileSidebarOpen(false)
    }
  }, [isMobile])

  /** 切换侧边栏：移动端控制抽屉，桌面端折叠并持久化到 localStorage。 */
  const handleToggleSidebar = useCallback((): void => {
    if (isMobile) {
      setMobileSidebarOpen((previousOpen) => !previousOpen)
      return
    }
    setSidebarCollapsed((previousCollapsed) => {
      const nextCollapsed = !previousCollapsed
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(nextCollapsed))
      } catch {
        // 本地存储不可用时仅保留内存状态
      }
      return nextCollapsed
    })
  }, [isMobile])

  /** 点击导航项后关闭移动端抽屉。 */
  const handleNavigate = useCallback((): void => {
    setMobileSidebarOpen(false)
  }, [])

  const pageTitle = resolvePageTitle(location.pathname)

  return (
    <div className={styles.shell}>
      <Sidebar
        collapsed={effectiveCollapsed}
        isMobile={isMobile}
        mobileOpen={mobileSidebarOpen}
        onNavigate={handleNavigate}
      />
      {isMobile && mobileSidebarOpen ? (
        <div className={styles.scrim} role="presentation" onClick={handleNavigate} />
      ) : null}
      <div className={styles.main} data-collapsed={effectiveCollapsed ? 'true' : 'false'}>
        <TopBar
          title={pageTitle}
          sidebarCollapsed={effectiveCollapsed}
          isMobile={isMobile}
          onToggleSidebar={handleToggleSidebar}
        />
        <main className={styles.content}>
          <div className={styles.contentInner}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}