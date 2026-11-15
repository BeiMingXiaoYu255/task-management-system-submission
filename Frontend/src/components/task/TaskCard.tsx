/**
 * 任务卡片：任务列表（团队任务、任务中心、首页复用）的统一展示单元。
 *
 * 展示内容：标题、优先级、状态、团队、发布者、截止时间（逾期高亮）、执行进度、
 * 当前用户个人状态，以及可选的快捷操作（接受/拒绝/提交完成）。
 * 快捷操作通过父组件传入的回调触发，卡片本身不直接发请求，保持展示组件无副作用。
 */

import { Link } from 'react-router-dom'

import Badge from '../ui/Badge'
import Button from '../ui/Button'
import type { TaskItem, TaskAssignmentItem } from '../../types/task'
import type { TaskActionKey } from '../../hooks/useTaskActions'
import {
  getAssignmentStatusLabel,
} from '../../utils/displayUtils'
import { checkOverdue, formatDateTime } from '../../utils/formatUtils'
import {
  buildCollaborationTaskPath,
  getCollaborationPhaseLabel,
  resolveTaskSourceTags,
} from '../collaboration/collaborationUtils'
import PriorityBadge from './PriorityBadge'
import StatusBadge from './StatusBadge'
import styles from './TaskCard.module.css'

/** TaskCard 组件属性。 */
export interface TaskCardProps {
  /** 任务列表项数据。 */
  task: TaskItem
  /** 是否展示团队名称（任务中心/待办场景需要，团队内列表不需要）。 */
  showTeam?: boolean
  /** 接受任务回调；不传则不展示接受按钮。 */
  onAccept?: (taskId: number) => void
  /** 拒绝任务回调；不传则不展示拒绝按钮。 */
  onDecline?: (taskId: number) => void
  /** 提交完成回调；不传则不展示提交按钮。 */
  onSubmit?: (taskId: number) => void
  /** 当前正在执行的操作（用于按钮互斥与加载态）。 */
  pendingAction?: TaskActionKey | null
}

/** 生成任务详情页路径：协作任务统一走协作任务详情路由。 */
export function buildTaskDetailPath(
  task: Pick<TaskItem, 'teamId' | 'id'> & { collaborationId?: number | null },
): string {
  if (task.collaborationId !== undefined && task.collaborationId !== null) {
    return buildCollaborationTaskPath(task.id)
  }
  return '/teams/' + task.teamId + '/tasks/' + task.id
}

/** 计算当前用户个人状态提示文案。 */
function resolveMyAssignmentHint(assignment: TaskAssignmentItem | null): string {
  if (assignment === null) {
    return ''
  }
  return 'My status: ' + getAssignmentStatusLabel(assignment.status)
}

/** 任务卡片组件。 */
export default function TaskCard({
  task,
  showTeam = false,
  onAccept,
  onDecline,
  onSubmit,
  pendingAction = null,
}: TaskCardProps) {
  const assignmentCount = task.assignments.length
  const archivedCount = task.assignments.filter((assignment) => assignment.status === 'archived').length
  const pendingReviewCount = task.assignments.filter(
    (assignment) => assignment.status === 'pendingReview',
  ).length
  const isOverdue =
    checkOverdue(task.dueAt) && task.status !== 'archived' && task.status !== 'cancelled'
  const myAssignment = task.myAssignment
  const isActionPending = pendingAction !== null
  const taskPath = buildTaskDetailPath(task)
  const sourceTags = resolveTaskSourceTags(task)

  /** 判断某个按钮是否应展示加载态。 */
  const isActionLoading = (actionKey: TaskActionKey): boolean => pendingAction === actionKey

  return (
    <article className={isOverdue ? styles.taskCard + ' ' + styles.overdueCard : styles.taskCard}>
      <header className={styles.cardHeader}>
        <Link to={taskPath} className={styles.titleLink}>
          {task.title}
        </Link>
        <div className={styles.badgeGroup}>
          <PriorityBadge priority={task.priority} />
          <StatusBadge status={task.status} kind="task" />
        </div>
      </header>

      {task.description ? <p className={styles.description}>{task.description}</p> : null}

      {sourceTags.length > 0 || task.collaborationPhase !== null ? (
        <div className={styles.sourceTagRow}>
          {sourceTags.map((sourceTag) => (
            <Badge key={sourceTag.key} variant="outline" size="small">
              {sourceTag.label}
            </Badge>
          ))}
          {task.collaborationPhase !== null ? (
            <Badge variant="default" size="small">
              Collaboration stage: {getCollaborationPhaseLabel(task.collaborationPhase)}
            </Badge>
          ) : null}
        </div>
      ) : null}

      <div className={styles.metaRow}>
        {showTeam ? <span className={styles.metaItem}>Team: {task.teamName}</span> : null}
        <span className={styles.metaItem}>Publisher: {task.createdByName}</span>
        <span className={isOverdue ? styles.overdueText : styles.metaItem}>
          Due: {formatDateTime(task.dueAt)}
          {isOverdue ? ' (Overdue)' : ''}
        </span>
        <span className={styles.metaItem}>
          Progress: {archivedCount} / {assignmentCount} completed
        </span>
        <span className={styles.metaItem}>
          {task.acceptanceMode === 'mandatory' ? 'Mandatory' : 'Optional'}
        </span>
        <span className={styles.metaItem}>
          {task.assignmentMode === 'specific' ? 'Specific Members' : 'Level Range'}
        </span>
      </div>

      <footer className={styles.cardFooter}>
        <span className={styles.hintText}>
          {resolveMyAssignmentHint(myAssignment)}
          {task.canReview && pendingReviewCount > 0 ? ' · ' + pendingReviewCount + ' pending my review' : ''}
        </span>
        <div className={styles.actionGroup}>
          {myAssignment?.status === 'pendingAcceptance' && onAccept ? (
            <Button
              size="small"
              onClick={() => onAccept(task.id)}
              disabled={isActionPending && !isActionLoading('accept')}
              loading={isActionLoading('accept')}
            >
              Accept
            </Button>
          ) : null}
          {myAssignment?.status === 'pendingAcceptance' && onDecline ? (
            <Button
              variant="ghost"
              size="small"
              onClick={() => onDecline(task.id)}
              disabled={isActionPending && !isActionLoading('decline')}
              loading={isActionLoading('decline')}
            >
              Reject
            </Button>
          ) : null}
          {myAssignment?.status === 'inProgress' && onSubmit ? (
            <Button
              size="small"
              onClick={() => onSubmit(task.id)}
              disabled={isActionPending && !isActionLoading('submit')}
              loading={isActionLoading('submit')}
            >
              Submit Completion
            </Button>
          ) : null}
          <Link to={taskPath} className={styles.detailLink}>
            View Details →
          </Link>
        </div>
      </footer>
    </article>
  )
}