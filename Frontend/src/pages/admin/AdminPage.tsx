/**
 * 管理后台页面：仅全局管理员/超级用户可访问。
 *
 * 页面仅负责权限兜底校验、Tab 切换与面板挂载；
 * 各业务面板（概览/用户/团队/数据库/审计）独立加载数据、独立处理错误。
 */

import { useState } from 'react'

import AuditPanel from '../../components/admin/AuditPanel'
import DatabasePanel from '../../components/admin/DatabasePanel'
import OverviewPanel from '../../components/admin/OverviewPanel'
import TeamsPanel from '../../components/admin/TeamsPanel'
import UsersPanel from '../../components/admin/UsersPanel'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import { useAuth } from '../../context/AuthContext'
import styles from './AdminPage.module.css'

/** 管理后台标签页键名。 */
type AdminTabKey = 'overview' | 'users' | 'teams' | 'database' | 'audit'

/** 管理后台标签页配置。 */
const ADMIN_TABS: { key: AdminTabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'users', label: 'Users' },
  { key: 'teams', label: 'Teams' },
  { key: 'database', label: 'Database' },
  { key: 'audit', label: 'Audit' },
]

/** 管理后台页面。 */
export default function AdminPage() {
  const { user } = useAuth()
  const [activeTabKey, setActiveTabKey] = useState<AdminTabKey>('overview')
  const globalRole = user?.user.globalRole ?? 'user'
  const isAdmin = globalRole === 'superAdmin' || globalRole === 'globalAdmin'
  const isSuperAdmin = globalRole === 'superAdmin'

  /** 非管理员直接给出无权限提示（路由层已有守卫，此处再兜底一次）。 */
  if (!isAdmin) {
    return (
      <div className={styles.pageRoot}>
        <EmptyState title="Access Denied" description="Only global admins and super admins can access this page." />
      </div>
    )
  }

  return (
    <div className={styles.pageRoot}>
      <PageHeader
        title="Admin Console"
        description="Manage system users, team certification, direct database access, and audit logs."
      />
      <Tabs
        items={ADMIN_TABS.map((tabItem) => ({ key: tabItem.key, label: tabItem.label }))}
        activeKey={activeTabKey}
        onChange={(key: string) => setActiveTabKey(key as AdminTabKey)}
      />
      <div className={styles.panelArea}>
        {activeTabKey === 'overview' && <OverviewPanel />}
        {activeTabKey === 'users' && <UsersPanel isSuperAdmin={isSuperAdmin} />}
        {activeTabKey === 'teams' && <TeamsPanel />}
        {activeTabKey === 'database' && <DatabasePanel />}
        {activeTabKey === 'audit' && <AuditPanel />}
      </div>
    </div>
  )
}
