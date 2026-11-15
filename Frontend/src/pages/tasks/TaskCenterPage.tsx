/**
 * 任务中心页：在“我参与的”和“我发布的”两类任务之间切换。
 *
 * 复用组件：TaskFilterBar（筛选/排序/团队过滤）、TaskCard（任务卡片与快捷操作）、
 * Pagination（分页）；筛选或角色切换时自动回到第一页。
 */

import { useCallback, useEffect, useMemo, useState } from 'react'

import * as taskApi from '../../api/taskApi'
import { useAuth } from '../../context/AuthContext'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import { useTaskActions } from '../../hooks/useTaskActions'
import type { MyTaskQuery } from '../../types/task'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Pagination from '../../components/ui/Pagination'
import Spinner from '../../components/ui/Spinner'
import Tabs from '../../components/ui/Tabs'
import TaskCard from '../../components/task/TaskCard'
import TaskFilterBar, {
  DEFAULT_TASK_FILTERS,
  type TaskFilterValues,
} from '../../components/task/TaskFilterBar'
import styles from './TaskCenterPage.module.css'

/** 任务中心角色视图。 */
type TaskCenterRole = 'created' | 'assigned'

/** 角色 Tab 配置。 */
const ROLE_TAB_ITEMS: { key: TaskCenterRole; label: string }[] = [
  { key: 'assigned', label: 'Assigned to Me' },
  { key: 'created', label: 'Created by Me' },
]

/** 任务中心页。 */
export default function TaskCenterPage() {
  const { user } = useAuth()
  const [role, setRole] = useState<TaskCenterRole>('assigned')
  const [filters, setFilters] = useState<TaskFilterValues>(DEFAULT_TASK_FILTERS)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal, resetPage } = pagination

  /** 拉取任务中心分页列表。 */
  const loadTasks = useCallback(() => {
    const query: MyTaskQuery = {
      role,
      status: filters.status || undefined,
      priority: filters.priority || undefined,
      keyword: filters.keyword.trim() || undefined,
      teamId: filters.teamId ? Number(filters.teamId) : undefined,
      sortBy: filters.sortBy,
      sortOrder: filters.sortOrder,
      page,
      pageSize,
    }
    return taskApi.listMyTasks(query)
  }, [
    role,
    filters.status,
    filters.priority,
    filters.keyword,
    filters.teamId,
    filters.sortBy,
    filters.sortOrder,
    page,
    pageSize,
  ])

  const { data, loading, error, reload } = useAsync(loadTasks, [loadTasks])
  const taskActions = useTaskActions(reload)
  const tasks = data?.items ?? []

  /** 列表加载完成后同步总条数。 */
  useEffect(() => {
    setTotal(data?.total ?? 0)
  }, [data, setTotal])

  /** 角色或筛选条件变化时回到第一页。 */
  useEffect(() => {
    resetPage()
  }, [role, filters.status, filters.priority, filters.keyword, filters.teamId, filters.sortBy, filters.sortOrder, resetPage])

  /** 团队筛选选项（从当前用户团队身份去重生成）。 */
  const teamOptions = useMemo(() => {
    const teamMap = new Map<number, string>()
    user?.teams.forEach((membership) => {
      teamMap.set(membership.teamId, membership.teamName)
    })
    return Array.from(teamMap.entries()).map(([teamIdValue, teamNameValue]) => ({
      value: teamIdValue,
      label: teamNameValue,
    }))
  }, [user])

  /** 空态描述根据角色区分。 */
  const emptyDescription =
    role === 'created'
      ? 'You have not published any tasks yet. Join a team to assign tasks to members.'
      : 'No tasks are assigned to you yet. Visit a team to find tasks you can join.'

  return (
    <div className="page-container">
      <PageHeader
        title="Task Center"
        description="View tasks assigned to you and tasks you created; accept, submit, and track reviews in one place."
        actions={
          <Button variant="secondary" onClick={reload} loading={loading}>
            Refresh
          </Button>
        }
      />

      <div className={styles.roleTabs}>
        <Tabs
          items={ROLE_TAB_ITEMS}
          activeKey={role}
          onChange={(nextKey) => setRole(nextKey as TaskCenterRole)}
        />
      </div>

      <TaskFilterBar
        values={filters}
        onChange={setFilters}
        teamOptions={teamOptions}
        onRefresh={reload}
        refreshing={loading}
      />

      {error ? (
        <section className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Reload
          </Button>
        </section>
      ) : loading && tasks.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading tasks...</span>
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState title="No tasks yet" description={emptyDescription} />
      ) : (
        <ul className={styles.taskList}>
          {tasks.map((task) => (
            <li key={task.id}>
              <TaskCard
                task={task}
                showTeam
                onAccept={(taskId) => void taskActions.accept(taskId)}
                onDecline={(taskId) => void taskActions.decline(taskId)}
                onSubmit={(taskId) => void taskActions.submit(taskId)}
                pendingAction={taskActions.pendingAction}
              />
            </li>
          ))}
        </ul>
      )}

      <Pagination
        page={pagination.page}
        pageSize={pagination.pageSize}
        total={pagination.total}
        onChange={setPage}
      />
    </div>
  )
}
