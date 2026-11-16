/**
 * 我的待办页：展示当前用户所有未归档任务待办，支持筛选/排序/分页与行内快捷操作。
 *
 * 功能要点：
 * 1. 顶部统计：总待办、待接受、进行中、待审核、已逾期（GET /todos/stats）；
 * 2. 列表：逾期行左侧危险色标记 + 文字提示；行内可直接接受/拒绝/提交完成；
 * 3. 点击标题进入任务详情页处理更复杂的审核流程；
 * 4. 操作成功后同时刷新列表与统计。
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import * as todoApi from '../../api/todoApi'
import { useAuth } from '../../context/AuthContext'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import { useTaskActions } from '../../hooks/useTaskActions'
import type { TodoItem, TodoQuery } from '../../types/todo'
import { getAssignmentStatusLabel } from '../../utils/displayUtils'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Pagination from '../../components/ui/Pagination'
import PriorityBadge from '../../components/task/PriorityBadge'
import Spinner from '../../components/ui/Spinner'
import StatusBadge from '../../components/task/StatusBadge'
import TodoFilterBar, {
  DEFAULT_TODO_FILTERS,
  type TodoFilterValues,
} from '../../components/task/TodoFilterBar'
import styles from './TodoListPage.module.css'

/** 我的待办页。 */
export default function TodoListPage() {
  const { user } = useAuth()
  const [filters, setFilters] = useState<TodoFilterValues>(DEFAULT_TODO_FILTERS)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal, resetPage } = pagination

  /** 拉取待办分页列表。 */
  const loadTodos = useCallback(() => {
    const query: TodoQuery = {
      status: filters.status || undefined,
      priority: filters.priority || undefined,
      teamId: filters.teamId ? Number(filters.teamId) : undefined,
      keyword: filters.keyword.trim() || undefined,
      sortBy: filters.sortBy,
      sortOrder: filters.sortOrder,
      includeArchived: filters.includeArchived ? true : undefined,
      page,
      pageSize,
    }
    return todoApi.listTodos(query)
  }, [
    filters.status,
    filters.priority,
    filters.teamId,
    filters.keyword,
    filters.sortBy,
    filters.sortOrder,
    filters.includeArchived,
    page,
    pageSize,
  ])

  const { data, loading, error, reload } = useAsync(loadTodos, [loadTodos])
  const todoStatsState = useAsync(() => todoApi.getTodoStats(), [])
  const taskActions = useTaskActions(() => {
    reload()
    todoStatsState.reload()
  })
  const todoItems = data?.items ?? []

  /** 列表加载完成后同步总条数。 */
  useEffect(() => {
    setTotal(data?.total ?? 0)
  }, [data, setTotal])

  /** 筛选条件变化时回到第一页。 */
  useEffect(() => {
    resetPage()
  }, [
    filters.status,
    filters.priority,
    filters.teamId,
    filters.keyword,
    filters.sortBy,
    filters.sortOrder,
    filters.includeArchived,
    resetPage,
  ])

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

  const stats = todoStatsState.data

  /** 渲染单条待办的快捷操作。 */
  const renderQuickActions = (todoItem: TodoItem) => {
    if (todoItem.assignmentStatus === 'pendingAcceptance') {
      return (
        <div className={styles.actionRow}>
          <Button
            size="small"
            loading={taskActions.pendingAction === 'accept'}
            disabled={taskActions.pendingAction !== null}
            onClick={() => void taskActions.accept(todoItem.taskId)}
          >
            Accept
          </Button>
          <Button
            variant="ghost"
            size="small"
            disabled={taskActions.pendingAction !== null}
            onClick={() => void taskActions.decline(todoItem.taskId)}
          >
            Reject
          </Button>
        </div>
      )
    }
    if (todoItem.assignmentStatus === 'inProgress') {
      return (
        <Button
          size="small"
          loading={taskActions.pendingAction === 'submit'}
          disabled={taskActions.pendingAction !== null}
          onClick={() => void taskActions.submit(todoItem.taskId)}
        >
          Submit Completion
        </Button>
      )
    }
    return <span className={styles.mutedText}>{getAssignmentStatusLabel(todoItem.assignmentStatus)}</span>
  }

  return (
    <div className="page-container">
      <PageHeader
        title="My To-dos"
        description="Handle tasks assigned to you: accept, submit completion, and track review results."
        actions={
          <Button
            variant="secondary"
            onClick={() => {
              reload()
              todoStatsState.reload()
            }}
            loading={loading}
          >
            Refresh
          </Button>
        }
      />

      <ul className={styles.statsRow}>
        <li className={styles.statCard}>
          <span className={styles.statValue}>{stats?.total ?? '—'}</span>
          <span className={styles.statLabel}>All Active</span>
        </li>
        <li className={styles.statCard}>
          <span className={styles.statValue}>{stats?.pendingAcceptance ?? '—'}</span>
          <span className={styles.statLabel}>Pending Acceptance</span>
        </li>
        <li className={styles.statCard}>
          <span className={styles.statValue}>{stats?.inProgress ?? '—'}</span>
          <span className={styles.statLabel}>In Progress</span>
        </li>
        <li className={styles.statCard}>
          <span className={styles.statValue}>{stats?.pendingReview ?? '—'}</span>
          <span className={styles.statLabel}>Pending Review</span>
        </li>
        <li className={styles.statCard}>
          <span className={styles.statValueDanger}>{stats?.overdue ?? '—'}</span>
          <span className={styles.statLabel}>Overdue</span>
        </li>
      </ul>

      <TodoFilterBar
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
      ) : loading && todoItems.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading to-dos...</span>
        </div>
      ) : todoItems.length === 0 ? (
        <EmptyState
          title="No to-dos yet"
          description="No tasks match the current filters. Check the Task Center for tasks you can join."
          action={
            <Link to="/tasks">
              <Button variant="secondary">Go to Task Center</Button>
            </Link>
          }
        />
      ) : (
        <ul className={styles.todoList}>
          {todoItems.map((todoItem) => (
            <li
              key={todoItem.assignmentId}
              className={
                todoItem.overdue ? styles.todoItem + ' ' + styles.overdueItem : styles.todoItem
              }
            >
              <div className={styles.todoMain}>
                <div className={styles.todoTitleRow}>
                  <Link
                    to={'/teams/' + todoItem.teamId + '/tasks/' + todoItem.taskId}
                    className={styles.todoTitle}
                  >
                    {todoItem.title}
                  </Link>
                  <PriorityBadge priority={todoItem.priority} />
                  <StatusBadge status={todoItem.assignmentStatus} kind="assignment" />
                  {todoItem.overdue ? <span className={styles.overdueTag}>Overdue</span> : null}
                </div>
                <div className={styles.todoMetaRow}>
                  <span>Team: {todoItem.teamName}</span>
                  <span>Publisher: {todoItem.createdByName}</span>
                  <span className={todoItem.overdue ? styles.overdueText : undefined}>
                    Due: {formatDateTime(todoItem.dueAt)}
                  </span>
                  <span>Assigned: {formatDateTime(todoItem.createdAt)}</span>
                </div>
              </div>
              <div className={styles.todoActions}>
                {renderQuickActions(todoItem)}
                <Link
                  to={'/teams/' + todoItem.teamId + '/tasks/' + todoItem.taskId}
                  className={styles.detailLink}
                >
                  View Details →
                </Link>
              </div>
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
