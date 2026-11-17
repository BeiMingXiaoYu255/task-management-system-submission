/**
 * 管理后台用户管理面板：支持关键词搜索、角色筛选、状态筛选与分页。
 *
 * 操作权限：
 * 1. 所有全局管理员可启用/禁用账号；
 * 2. 仅超级用户可设置/取消全局管理员（普通用户 ↔ 全局管理员）。
 * 重要操作统一走二次确认弹窗，成功后刷新当前页数据。
 */

import { useCallback, useEffect, useState } from 'react'

import { listAdminUsers, setGlobalRole, setUserStatus } from '../../api/adminApi'
import type { AdminUserItem } from '../../types/admin'
import { GLOBAL_ROLE_LABELS } from '../../utils/displayUtils'
import { formatDate } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import EmptyState from '../ui/EmptyState'
import Input from '../ui/Input'
import Pagination from '../ui/Pagination'
import Select from '../ui/Select'
import Spinner from '../ui/Spinner'
import Table from '../ui/Table'
import { useToast } from '../../context/ToastContext'
import styles from './UsersPanel.module.css'

/** 用户列表每页条数。 */
const PAGE_SIZE = 20

/** 待确认的管理操作。 */
interface PendingAction {
  /** 操作类型。 */
  actionType: 'status' | 'globalRole'
  /** 目标用户。 */
  userItem: AdminUserItem
}

/** 用户管理面板属性。 */
interface UsersPanelProps {
  /** 当前登录用户是否为超级用户。 */
  isSuperAdmin: boolean
}

/** 角色筛选选项。 */
const ROLE_FILTER_OPTIONS = [
  { value: '', label: 'All Roles' },
  { value: 'superAdmin', label: 'Super Admin' },
  { value: 'globalAdmin', label: 'Global Admin' },
  { value: 'user', label: 'Standard User' },
]

/** 状态筛选选项。 */
const ACTIVE_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'true', label: 'Enabled' },
  { value: 'false', label: 'Disabled' },
]

/** 管理后台用户管理面板。 */
export default function UsersPanel({ isSuperAdmin }: UsersPanelProps) {
  const { showToast } = useToast()
  const [users, setUsers] = useState<AdminUserItem[]>([])
  const [total, setTotal] = useState<number>(0)
  const [page, setPage] = useState<number>(1)
  const [keywordDraft, setKeywordDraft] = useState<string>('')
  const [keyword, setKeyword] = useState<string>('')
  const [globalRoleFilter, setGlobalRoleFilter] = useState<string>('')
  const [activeFilter, setActiveFilter] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const [actionLoading, setActionLoading] = useState<boolean>(false)

  /** 按当前筛选条件加载用户分页列表。 */
  const loadUsers = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const pageResult = await listAdminUsers({
        keyword: keyword === '' ? undefined : keyword,
        globalRole: globalRoleFilter === '' ? undefined : globalRoleFilter,
        isActive: activeFilter === '' ? undefined : activeFilter === 'true',
        page,
        pageSize: PAGE_SIZE,
      })
      setUsers(pageResult.items)
      setTotal(pageResult.total)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [keyword, globalRoleFilter, activeFilter, page])

  useEffect(() => {
    void loadUsers()
  }, [loadUsers])

  /** 点击搜索：重置到第一页并应用关键词。 */
  const handleSearch = (): void => {
    setPage(1)
    setKeyword(keywordDraft.trim())
  }

  /** 重置全部筛选条件。 */
  const handleResetFilters = (): void => {
    setKeywordDraft('')
    setKeyword('')
    setGlobalRoleFilter('')
    setActiveFilter('')
    setPage(1)
  }

  /** 角色筛选变化。 */
  const handleRoleFilterChange = (value: string | number): void => {
    setPage(1)
    setGlobalRoleFilter(String(value))
  }

  /** 状态筛选变化。 */
  const handleActiveFilterChange = (value: string | number): void => {
    setPage(1)
    setActiveFilter(String(value))
  }

  /** 执行待确认的用户管理操作。 */
  const handleConfirmAction = async (): Promise<void> => {
    if (pendingAction === null) {
      return
    }
    setActionLoading(true)
    try {
      if (pendingAction.actionType === 'status') {
        const updatedUser = await setUserStatus(
          pendingAction.userItem.id,
          !pendingAction.userItem.isActive,
        )
        showToast(updatedUser.isActive ? 'Account enabled' : 'Account disabled', 'success')
      } else {
        const nextRole = pendingAction.userItem.globalRole === 'globalAdmin' ? 'user' : 'globalAdmin'
        await setGlobalRole(pendingAction.userItem.id, nextRole)
        showToast(nextRole === 'globalAdmin' ? 'Global admin role granted' : 'Global admin role revoked', 'success')
      }
      setPendingAction(null)
      await loadUsers()
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Action failed. Please try again later.', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  /** 生成确认弹窗文案。 */
  const resolveConfirmContent = (): { title: string; description: string; danger: boolean } => {
    if (pendingAction === null) {
      return { title: 'Confirm Action', description: '', danger: false }
    }
    const targetUser = pendingAction.userItem
    if (pendingAction.actionType === 'status') {
      const willDisable = targetUser.isActive
      return {
        title: willDisable ? 'Disable Account' : 'Enable Account',
        description: 'Are you sure you want to ' + (willDisable ? 'disable' : 'enable') + ' user "' + targetUser.nickname + '"?',
        danger: willDisable,
      }
    }
    const isGranting = targetUser.globalRole !== 'globalAdmin'
    return {
      title: isGranting ? 'Grant Global Admin' : 'Revoke Global Admin',
      description:
        'Are you sure you want to ' + (isGranting ? 'grant global admin to "' : 'revoke global admin from "') + targetUser.nickname +
        '"?',
      danger: false,
    }
  }

  const confirmContent = resolveConfirmContent()

  return (
    <div className={styles.panelLayout}>
      <div className={styles.filterRow}>
        <div className={styles.keywordArea}>
          <Input
            value={keywordDraft}
            onChange={(event) => setKeywordDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                handleSearch()
              }
            }}
            placeholder="Search username / nickname / email"
          />
        </div>
        <Select value={globalRoleFilter} onChange={handleRoleFilterChange} options={ROLE_FILTER_OPTIONS} />
        <Select value={activeFilter} onChange={handleActiveFilterChange} options={ACTIVE_FILTER_OPTIONS} />
        <Button variant="secondary" onClick={handleSearch}>Search</Button>
        <Button variant="ghost" onClick={handleResetFilters}>Reset</Button>
      </div>

      {errorMessage !== null ? (
        <EmptyState
          title="Failed to load users"
          description={errorMessage}
          action={<Button variant="secondary" onClick={() => void loadUsers()}>Reload</Button>}
        />
      ) : loading ? (
        <div className={styles.stateArea}><Spinner /><span>Loading users ...</span></div>
      ) : users.length === 0 ? (
        <EmptyState title="No matching users" description="Adjust your keywords or filters and try again." />
      ) : (
        <>
          <Table
            columns={[
              {
                key: 'username',
                title: 'Username',
                width: 140,
                render: (row: AdminUserItem) => <span className={styles.username}>{row.username}</span>,
              },
              { key: 'nickname', title: 'Nickname', width: 130, render: (row: AdminUserItem) => row.nickname },
              {
                key: 'email',
                title: 'Email',
                render: (row: AdminUserItem) => row.email ?? '—',
              },
              {
                key: 'globalRole',
                title: 'Global Role',
                width: 120,
                render: (row: AdminUserItem) => (
                  <Badge variant={row.globalRole === 'user' ? 'outline' : 'solid'}>
                    {GLOBAL_ROLE_LABELS[row.globalRole]}
                  </Badge>
                ),
              },
              {
                key: 'isActive',
                title: 'Status',
                width: 90,
                render: (row: AdminUserItem) => (
                  <Badge variant={row.isActive ? 'default' : 'outline'}>
                    {row.isActive ? 'Enabled' : 'Disabled'}
                  </Badge>
                ),
              },
              { key: 'teamCount', title: 'Teams', width: 80, align: 'right', render: (row: AdminUserItem) => row.teamCount },
              {
                key: 'createdAt',
                title: 'Registered At',
                width: 120,
                render: (row: AdminUserItem) => formatDate(row.createdAt),
              },
              {
                key: 'actions',
                title: 'Actions',
                width: 190,
                render: (row: AdminUserItem) => (
                  <div className={styles.actionRow}>
                    {row.globalRole === 'superAdmin' ? (
                      <span className={styles.protectedText}>Built-in Account</span>
                    ) : (
                      <Button
                        size="small"
                        variant={row.isActive ? 'danger' : 'secondary'}
                        onClick={() => setPendingAction({ actionType: 'status', userItem: row })}
                      >
                        {row.isActive ? 'Disable' : 'Enable'}
                      </Button>
                    )}
                    {isSuperAdmin && row.globalRole !== 'superAdmin' && (
                      <Button
                        size="small"
                        variant="ghost"
                        onClick={() => setPendingAction({ actionType: 'globalRole', userItem: row })}
                      >
                        {row.globalRole === 'globalAdmin' ? 'Revoke Admin' : 'Make Admin'}
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={users}
            rowKey={(row: AdminUserItem) => row.id}
            emptyText="No user data yet"
          />
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </>
      )}

      <ConfirmDialog
        open={pendingAction !== null}
        title={confirmContent.title}
        description={confirmContent.description}
        danger={confirmContent.danger}
        loading={actionLoading}
        onConfirm={() => void handleConfirmAction()}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  )
}
