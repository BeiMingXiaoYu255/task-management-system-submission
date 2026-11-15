/**
 * 团队详情-任务 Tab：团队任务列表（筛选/排序/分页）、发布任务、行内快捷操作。
 *
 * 发布权限：团队管理员/子管理员，或当前级别 canCreateTask=true 的成员。
 * 数据流：筛选条件与分页变化 → useAsync 自动重新请求；任务操作成功后 reload 列表。
 */

import { useCallback, useEffect, useState } from 'react'

import * as taskApi from '../../api/taskApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import { useTaskActions } from '../../hooks/useTaskActions'
import type { CreateTaskPayload, TaskDetail } from '../../types/task'
import type { TeamDetail } from '../../types/team'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Pagination from '../ui/Pagination'
import Spinner from '../ui/Spinner'
import TaskCard from '../task/TaskCard'
import TaskFilterBar, { DEFAULT_TASK_FILTERS, type TaskFilterValues } from '../task/TaskFilterBar'
import TaskForm from '../task/TaskForm'
import styles from './TeamTasksTab.module.css'

/** TeamTasksTab 组件属性。 */
export interface TeamTasksTabProps {
  /** 团队详情（含当前用户角色与级别）。 */
  team: TeamDetail
}

/** 团队详情-任务 Tab。 */
export default function TeamTasksTab({ team }: TeamTasksTabProps) {
  const { showToast } = useToast()
  const [filters, setFilters] = useState<TaskFilterValues>(DEFAULT_TASK_FILTERS)
  const [publishDialogOpen, setPublishDialogOpen] = useState<boolean>(false)
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal, resetPage } = pagination

  /** 拉取团队任务分页列表。 */
  const loadTasks = useCallback(
    () =>
      taskApi.listTeamTasks(team.id, {
        status: filters.status || undefined,
        priority: filters.priority || undefined,
        keyword: filters.keyword.trim() || undefined,
        sortBy: filters.sortBy,
        sortOrder: filters.sortOrder,
        page,
        pageSize,
      }),
    [team.id, filters.status, filters.priority, filters.keyword, filters.sortBy, filters.sortOrder, page, pageSize],
  )

  const { data, loading, error, reload } = useAsync(loadTasks, [loadTasks])
  const taskActions = useTaskActions(reload)
  const tasks = data?.items ?? []

  /** 列表加载完成后同步总条数。 */
  useEffect(() => {
    setTotal(data?.total ?? 0)
  }, [data, setTotal])

  /** 筛选条件变化时回到第一页。 */
  useEffect(() => {
    resetPage()
  }, [filters.status, filters.priority, filters.keyword, filters.sortBy, filters.sortOrder, resetPage])

  const currentLevel = team.levels.find(
    (teamLevel) => teamLevel.levelOrder === team.currentUserLevelOrder,
  )
  const canPublish = team.currentUserRole !== 'member' || currentLevel?.canCreateTask === true

  /** 发布任务：成功后关闭弹窗并刷新列表；返回任务详情供 AI 自动分配结果提示。 */
  const handleCreateTask = async (payload: CreateTaskPayload): Promise<TaskDetail> => {
    const createdTask = await taskApi.createTask(team.id, payload)
    showToast('Task published.', 'success')
    setPublishDialogOpen(false)
    reload()
    return createdTask
  }

  return (
    <div className={styles.tasksTab}>
      <header className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Team Tasks</h2>
          <p className={styles.sectionDescription}>
            Filter tasks by status, priority, and keyword. Click a task card to open details.
          </p>
        </div>
        {canPublish ? (
          <Button onClick={() => setPublishDialogOpen(true)}>Publish Task</Button>
        ) : (
          <span className={styles.permissionHint}>Your level cannot publish tasks.</span>
        )}
      </header>

      <TaskFilterBar
        values={filters}
        onChange={setFilters}
        onRefresh={reload}
        refreshing={loading}
      />

      {error ? (
        <div className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Retry
          </Button>
        </div>
      ) : loading && tasks.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="small" />
          <span>Loading tasks...</span>
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No tasks yet"
          description={canPublish ? 'Click Publish Task in the upper right to start collaborating.' : 'The team has no tasks yet.'}
          action={
            canPublish ? (
              <Button onClick={() => setPublishDialogOpen(true)}>Publish the First Task</Button>
            ) : undefined
          }
        />
      ) : (
        <ul className={styles.taskList}>
          {tasks.map((task) => (
            <li key={task.id}>
              <TaskCard
                task={task}
                onAccept={(taskId) => void taskActions.accept(taskId)}
                onDecline={(taskId) => void taskActions.decline(taskId)}
                onSubmit={(taskId) => void taskActions.submit(taskId)}
                pendingAction={taskActions.pendingAction}
              />
            </li>
          ))}
        </ul>
      )}

      {pagination.total > 0 ? (
        <Pagination
          page={pagination.page}
          pageSize={pagination.pageSize}
          total={pagination.total}
          onChange={setPage}
        />
      ) : null}

      {publishDialogOpen ? (
        <TaskForm
          open={publishDialogOpen}
          team={team}
          onCancel={() => setPublishDialogOpen(false)}
          onSubmit={handleCreateTask}
        />
      ) : null}
    </div>
  )
}
