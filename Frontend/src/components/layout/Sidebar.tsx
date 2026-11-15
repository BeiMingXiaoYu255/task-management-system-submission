/**
 * 侧边栏：展示品牌标识与主导航，支持桌面折叠与移动端抽屉两种形态。
 * 管理后台入口仅对 globalAdmin / superAdmin 可见。
 */

import { NavLink } from 'react-router-dom'

import { useAuth } from '../../context/AuthContext'
import { GLOBAL_ROLE_LABELS } from '../../utils/displayUtils'
import { NAVIGATION_ITEMS } from './navigationConfig'
import styles from './Sidebar.module.css'

/** 侧边栏属性。 */
export interface SidebarProps {
  /** 桌面模式是否折叠为图标栏。 */
  collapsed: boolean
  /** 是否移动端视口。 */
  isMobile: boolean
  /** 移动端抽屉是否展开。 */
  mobileOpen: boolean
  /** 点击导航项后的回调（移动端用于关闭抽屉）。 */
  onNavigate: () => void
}

/** 侧边栏组件。 */
export function Sidebar({ collapsed, isMobile, mobileOpen, onNavigate }: SidebarProps) {
  const { user } = useAuth()
  const globalRole = user?.user.globalRole ?? 'user'
  const isAdmin = globalRole === 'superAdmin' || globalRole === 'globalAdmin'
  const visibleItems = NAVIGATION_ITEMS.filter((item) => !item.adminOnly || isAdmin)

  const classNames = [styles.sidebar]
  if (collapsed) {
    classNames.push(styles.collapsed)
  }
  if (isMobile) {
    classNames.push(styles.mobile)
  }
  if (isMobile && mobileOpen) {
    classNames.push(styles.mobileOpen)
  }

  return (
    <aside className={classNames.join(' ')} aria-label="Main navigation">
      <div className={styles.brand}>
        <span className={styles.brandMark}>T</span>
        {collapsed ? null : <span className={styles.brandText}>Task Management</span>}
      </div>
      <nav className={styles.navigation}>
        {visibleItems.map((navigationItem) => {
          const IconComponent = navigationItem.icon
          return (
            <NavLink
              key={navigationItem.path}
              to={navigationItem.path}
              title={collapsed ? navigationItem.label : undefined}
              className={({ isActive }) =>
                [styles.navItem, isActive ? styles.activeNavItem : ''].filter(Boolean).join(' ')
              }
              onClick={onNavigate}
            >
              <IconComponent size={16} className={styles.navIcon} />
              {collapsed ? null : <span className={styles.navLabel}>{navigationItem.label}</span>}
            </NavLink>
          )
        })}
      </nav>
      <div className={styles.footer}>
        {collapsed ? null : (
          <span className={styles.userInfo}>
            {user ? user.user.nickname + ' · ' + GLOBAL_ROLE_LABELS[globalRole] : 'LAN Collaboration Edition'}
          </span>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
