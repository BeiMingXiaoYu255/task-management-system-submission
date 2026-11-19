/**
 * 协作任务列表：协作详情页的任务区，展示阶段、执行进度并提供新建入口。
 *
 * 仅负责展示与分页渲染，数据加载与新建流程由协作详情页统一处理。
 */

import { Link } from 'react-router-dom'

import type { CollaborationTaskItem } from '../../types/collaboration'
import { checkOverdue, formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Pagination from '../ui/Pagination'
import Spinner from '../ui/Spinner'
import PriorityBadge from '../task/PriorityBadge'
import StatusBadge from '../task/StatusBadge'
import {
  buildCollaborationTaskPath,
  getCollaborationPhaseLabel,
} from './collaborationUtils'
import styles from './CollaborationTaskList.module.css'

/** 协作任务列表属性。 */
export interface CollaborationTaskListProps {
  /** 当前页任务。 */
  tasks: CollaborationTaskItem[]
  /** 是否加载中。 */
  loading: boolean
  /** 错误提示。 */
  error: string | null
  /** 是否可新建协作任务。 */
  canCreateTask: boolean
  /** 新建协作任务回调。 */
  onCreate: () => void
  /** 重新加载回调。 */
  onReload: () => void
  /** 分页状态。 */
  page: number
  /** 每页条数。 */
  pageSize: number
  /** 总条数。 */
  total: number
  /** 页码变化回调。 */
  onPageChange: (page: number) => void
}

/** 协作任务列表组件。 */
export default function CollaborationTaskList({
  tasks,
  loading,
  error,
  canCreateTask,
  onCreate,
  onReload,
  page,
  pageSize,
  total,
  onPageChange,
}: CollaborationTaskListProps) {
  return (
    <section className={styles.taskSection}>
      <header className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Collaboration Tasks</h2>
          <p className={styles.sectionDescription}>
            The receiver liaison confirms collaboration tasks and assigns assignees. After submission, both parties review the work.
          </p>
        </div>
        {canCreateTask ? <Button onClick={onCreate}>New Collaboration Task</Button> : null}
      </header>

      {error !== null ? (
        <div className={styles.errorBox}>
          <span>{error}</span>
          <Button variant="secondary" size="small" onClick={onReload}>
            Reload
          </Button>
        </div>
      ) : loading && tasks.length === 0 ? (
        <div className={styles.loadingBox}>
          <Spinner size="small" />
          <span>Loading collaboration tasks...</span>
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No collaboration tasks yet"
          description={
            canCreateTask
              ? 'Click "New Collaboration Task" in the top right to dispatch a task to the collaborating unit.'
              : 'The collaborating unit has not dispatched any collaboration tasks yet.'
          }
          action={canCreateTask ? <Button onClick={onCreate}>Create the First Collaboration Task</Button> : undefined}
        />
      ) : (
        <ul className={styles.taskList}>
          {tasks.map((task) => {
            const archivedCount = task.assignments.filter(
              (assignment) => assignment.status === 'archived',
            ).length
            const isOverdue =
              checkOverdue(task.dueAt) && task.status !== 'archived' && task.status !== 'cancelled'
            return (
              <li key={task.id} className={styles.taskItem}>
                <div className={styles.taskHeader}>
                  <Link to={buildCollaborationTaskPath(task.id)} className={styles.titleLink}>
                    {task.title}
                  </Link>
                  <div className={styles.badgeGroup}>
                    <PriorityBadge priority={task.priority} />
                    <StatusBadge status={task.status} kind="task" />
                    <Badge variant="outline" size="small">
                      {getCollaborationPhaseLabel(task.collaborationPhase)}
                    </Badge>
                  </div>
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.metaItem}>Publisher: {task.createdByName}</span>
                  <span className={isOverdue ? styles.overdueText : styles.metaItem}>
                    Due: {formatDateTime(task.dueAt)}
                    {isOverdue ? ' (Overdue)' : ''}
                  </span>
                  <span className={styles.metaItem}>
                    Assignees: {task.assignments.length} · Completed: {archivedCount}
                  </span>
                  <span className={styles.metaItem}>
                    {task.acceptanceMode === 'mandatory' ? 'Mandatory Acceptance' : 'Optional Acceptance'}
                  </span>
                </div>
                <div className={styles.taskFooter}>
                  <Link to={buildCollaborationTaskPath(task.id)} className={styles.detailLink}>
                    View collaboration task details →
                  </Link>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {total > 0 ? (
        <Pagination page={page} pageSize={pageSize} total={total} onChange={onPageChange} />
      ) : null}
    </section>
  )
}
