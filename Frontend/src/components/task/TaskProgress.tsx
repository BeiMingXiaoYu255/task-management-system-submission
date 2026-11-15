/**
 * 任务执行进度：展示所有执行人的个人状态与整体完成占比。
 *
 * 完成度 = 已归档分配数 / 总分配数；被拒绝的可选任务已从分配列表移除，
 * 因此这里直接以任务详情返回的 assignments 为准。
 */

import Avatar from '../ui/Avatar'
import ProgressBar from '../ui/ProgressBar'
import { formatDateTime } from '../../utils/formatUtils'
import type { TaskItem } from '../../types/task'
import StatusBadge from './StatusBadge'
import styles from './TaskProgress.module.css'

/** TaskProgress 组件属性。 */
export interface TaskProgressProps {
  /** 任务数据。 */
  task: TaskItem
}

/** 任务执行进度组件。 */
export default function TaskProgress({ task }: TaskProgressProps) {
  const totalCount = task.assignments.length
  const archivedCount = task.assignments.filter((assignment) => assignment.status === 'archived').length
  const completedPercent = totalCount === 0 ? 0 : Math.round((archivedCount / totalCount) * 100)

  return (
    <section className={styles.progressSection}>
      <header className={styles.progressHeader}>
        <h3 className={styles.progressTitle}>Execution Progress</h3>
        <span className={styles.progressSummary}>
          {archivedCount} / {totalCount} completed · {completedPercent}%
        </span>
      </header>
      <ProgressBar value={archivedCount} max={totalCount === 0 ? 1 : totalCount} />
      {totalCount === 0 ? (
        <p className={styles.emptyHint}>No assignees yet</p>
      ) : (
        <ul className={styles.assignmentList}>
          {task.assignments.map((assignment) => (
            <li key={assignment.id} className={styles.assignmentItem}>
              <Avatar name={assignment.nickname} src={assignment.avatar ?? undefined} size="small" />
              <div className={styles.assignmentMain}>
                <span className={styles.assignmentName}>{assignment.nickname}</span>
                {assignment.reviewComment ? (
                  <span className={styles.assignmentComment}>
                    Latest comment: {assignment.reviewComment}
                  </span>
                ) : (
                  <span className={styles.assignmentComment}>
                    Submitted {formatDateTime(assignment.submittedAt)}
                  </span>
                )}
              </div>
              <StatusBadge status={assignment.status} kind="assignment" />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
