/**
 * 顶栏用户菜单：展示头像/昵称/全局角色，提供个人资料、设置、管理后台与退出登录入口。
 */

import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { GLOBAL_ROLE_LABELS } from '../../utils/displayUtils'
import Avatar from '../ui/Avatar'
import Dropdown, { type DropdownItem } from '../ui/Dropdown'
import styles from './UserMenu.module.css'

/** 顶栏用户菜单。 */
export function UserMenu() {
  const { user, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  if (user === null) {
    return null
  }

  const displayName = user.user.nickname || user.user.username
  const globalRole = user.user.globalRole
  const isAdmin = globalRole === 'superAdmin' || globalRole === 'globalAdmin'

  /** 退出登录并跳转登录页。 */
  const handleLogout = async (): Promise<void> => {
    await logout()
    showToast('Signed out', 'success')
    navigate('/login', { replace: true })
  }

  const menuItems: DropdownItem[] = [
    { key: 'profile', label: 'Profile', onClick: () => navigate('/profile') },
    { key: 'settings', label: 'Settings', onClick: () => navigate('/settings') },
  ]
  if (isAdmin) {
    menuItems.push({ key: 'admin', label: 'Admin Console', onClick: () => navigate('/admin') })
  }
  menuItems.push({
    key: 'logout',
    label: 'Sign Out',
    danger: true,
    onClick: () => {
      void handleLogout()
    },
  })

  const trigger = (
    <span className={styles.trigger}>
      <Avatar name={displayName} src={user.user.avatar} size="small" />
      <span className={styles.userText}>
        <span className={styles.nickname}>{displayName}</span>
        <span className={styles.role}>{GLOBAL_ROLE_LABELS[globalRole]}</span>
      </span>
    </span>
  )

  return <Dropdown trigger={trigger} items={menuItems} align="right" />
}

export default UserMenu
