/**
 * 侧边栏导航配置与页面标题解析：集中维护路径、文案与图标。
 */

import type { ComponentType } from 'react'

import { CollaborationNavIcon } from '../collaboration/CollaborationNavIcon'
import {
  IconAdmin,
  IconDashboard,
  IconProfile,
  IconSettings,
  IconTask,
  IconTeam,
  IconTodo,
  type LayoutIconProps,
} from './LayoutIcons'

/** 侧边栏导航项。 */
export interface NavigationItem {
  /** 目标路由路径。 */
  path: string
  /** 显示文案。 */
  label: string
  /** 图标组件。 */
  icon: ComponentType<LayoutIconProps>
  /** 是否仅全局管理员可见。 */
  adminOnly?: boolean
}

/** 侧边栏导航项列表（顺序即展示顺序）。 */
export const NAVIGATION_ITEMS: NavigationItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: IconDashboard },
  { path: '/teams', label: 'Teams', icon: IconTeam },
  { path: '/todos', label: 'To-dos', icon: IconTodo },
  { path: '/tasks', label: 'Tasks', icon: IconTask },
  { path: '/collaborations', label: 'Collaborations', icon: CollaborationNavIcon },
  { path: '/profile', label: 'Profile', icon: IconProfile },
  { path: '/settings', label: 'Settings', icon: IconSettings },
  { path: '/admin', label: 'Admin Console', icon: IconAdmin, adminOnly: true },
]

/** 路径 → 页面标题的匹配规则（按顺序优先匹配）。 */
const PAGE_TITLE_RULES: { pattern: RegExp; title: string }[] = [
  { pattern: /^\/teams\/[^/]+\/tasks\/[^/]+$/, title: 'Task Details' },
  { pattern: /^\/teams\/[^/]+$/, title: 'Team Details' },
  { pattern: /^\/teams$/, title: 'My Teams' },
  { pattern: /^\/collaboration-tasks\/[^/]+$/, title: 'Collaboration Task Details' },
  { pattern: /^\/collaborations\/[^/]+$/, title: 'Collaboration Details' },
  { pattern: /^\/collaborations$/, title: 'Collaboration Center' },
  { pattern: /^\/notifications$/, title: 'Notification Center' },
  { pattern: /^\/tasks$/, title: 'Task Center' },
  { pattern: /^\/todos$/, title: 'My To-dos' },
  { pattern: /^\/dashboard$/, title: 'Dashboard' },
  { pattern: /^\/profile$/, title: 'Profile' },
  { pattern: /^\/settings$/, title: 'Settings' },
  { pattern: /^\/admin$/, title: 'Admin Console' },
]

/** 根据当前路径解析顶栏页面标题。 */
export function resolvePageTitle(pathname: string): string {
  const matchedRule = PAGE_TITLE_RULES.find((rule) => rule.pattern.test(pathname))
  return matchedRule ? matchedRule.title : 'Task Management System'
}