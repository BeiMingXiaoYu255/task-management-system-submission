/**
 * 子团队任务面板：展示指定子团队的任务分页列表，支持接受/提交等快捷操作。
 *
 * 数据来源：GET /teams/{teamId}/sub-teams/{subTeamId}/tasks。
 */

import { useCallback, useEffect } from 'react'

import { listSubTeamTasks } from '../../api/teamApi'
import { useAsync } from '../../hooks/useAsync'
import { usePagination } from '../../hooks/usePagination'
import { useTaskActions } from '../../hooks/useTaskActions'
import type { SubTeamItem } from '../../types/collaboration'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Pagination from '../ui/Pagination'
import Spinner from '../ui/Spinner'
import TaskCard from '../task/TaskCard'
import styles from './SubTeamTasksPanel.module.css'

/** 子团队任务面板属性。 */
export interface SubTeamTasksPanelProps {
  /** 父团队 ID。 */
  teamId: number
  /** 目标子团队。 */
  subTeam: SubTeamItem
  /** 收起回调。 */
  onClose: () => void
}

/** 子团队任务面板。 */
export default function SubTeamTasksPanel({ teamId, subTeam, onClose }: SubTeamTasksPanelProps) {
  const pagination = usePagination()
  const { page, pageSize, setPage, setTotal } = pagination

  /** 拉取子团队任务。 */
  const loadTasks = useCallback(
    () => listSubTeamTasks(teamId, subTeam.id, { page, pageSize }),
    [teamId, subTeam.id, page, pageSize],
  )

  const { data, loading, error, reload } = useAsync(loadTasks, [loadTasks])
  const taskActions = useTaskActions(reload)
  const tasks = data?.items ?? []

  /** 同步总数。 */
  useEffect(() => {
    setTotal(data?.total ?? 0)
  }, [data, setTotal])

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div>
          <h3 className={styles.panelTitle}>Sub-team Tasks · {subTeam.name}</h3>
          <p className={styles.panelDescription}>
            Visible only to sub-team members and parent team admins. Click a task card to open its details.
          </p>
        </div>
        <Button variant="ghost" size="small" onClick={onClose}>
          Hide
        </Button>
      </header>

      {error !== null ? (
        <div className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Reload
          </Button>
        </div>
      ) : loading && tasks.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="small" />
          <span>Loading sub-team tasks...</span>
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState title="No sub-team tasks yet" description="Select this sub-team as the group when publishing a task." />
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
        <Pagination page={page} pageSize={pageSize} total={pagination.total} onChange={setPage} />
      ) : null}
    </section>
  )
}