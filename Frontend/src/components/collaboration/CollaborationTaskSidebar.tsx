/**
 * 协作任务侧栏：接收方确认入口、我的执行操作、协作信息与时间信息。
 *
 * 纯展示组件：所有操作回调由协作任务详情页注入，数据来自已加载的任务详情。
 */

import { Link } from 'react-router-dom'

import type { TaskActionKey } from '../../hooks/useTaskActions'
import type { CollaborationTaskDetail } from '../../types/collaboration'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../ui/Button'
import StatusBadge from '../task/StatusBadge'
import { getCollaborationPhaseLabel } from './collaborationUtils'
import styles from './CollaborationTaskSidebar.module.css'

/** 协作任务侧栏属性。 */
export interface CollaborationTaskSidebarProps {
  /** 协作任务详情。 */
  task: CollaborationTaskDetail
  /** 发起单位展示名称。 */
  sourceUnitName: string
  /** 接收单位展示名称。 */
  targetUnitName: string
  /** 当前正在执行的任务操作。 */
  pendingAction: TaskActionKey | null
  /** 接受任务回调。 */
  onAccept: () => void
  /** 拒绝任务回调。 */
  onDecline: () => void
  /** 提交完成回调。 */
  onSubmit: () => void
  /** 打开接收方确认弹窗回调。 */
  onOpenConfirm: () => void
}

/** 协作任务侧栏组件。 */
export default function CollaborationTaskSidebar({
  task,
  sourceUnitName,
  targetUnitName,
  pendingAction,
  onAccept,
  onDecline,
  onSubmit,
  onOpenConfirm,
}: CollaborationTaskSidebarProps) {
  const myAssignment = task.myAssignment

  return (
    <aside className={styles.sideColumn}>
      {task.canConfirmTask ? (
        <section className={styles.sideSection}>
          <h2 className={styles.sideTitle}>Receiver Liaison Actions</h2>
          <p className={styles.hintText}>
            When accepting, assign assignees from the receiving unit. If rejected, the task is cancelled and the initiator is notified.
          </p>
          <Button onClick={onOpenConfirm}>Process Collaboration Task</Button>
        </section>
      ) : null}

      <section className={styles.sideSection}>
        <h2 className={styles.sideTitle}>My Assignment</h2>
        {myAssignment === null ? (
          <p className={styles.hintText}>You are not an assignee of this task. You can view its progress and review records.</p>
        ) : (
          <div className={styles.myAssignmentBlock}>
            <div className={styles.myAssignmentRow}>
              <span className={styles.hintText}>My Status</span>
              <StatusBadge status={myAssignment.status} kind="assignment" />
            </div>
            {myAssignment.status === 'pendingAcceptance' ? (
              <div className={styles.actionRow}>
                <Button
                  onClick={onAccept}
                  loading={pendingAction === 'accept'}
                  disabled={pendingAction !== null}
                >
                  Accept Task
                </Button>
                <Button
                  variant="danger"
                  onClick={onDecline}
                  loading={pendingAction === 'decline'}
                  disabled={pendingAction !== null}
                >
                  Reject Task
                </Button>
              </div>
            ) : null}
            {myAssignment.status === 'inProgress' ? (
              <Button
                onClick={onSubmit}
                loading={pendingAction === 'submit'}
                disabled={pendingAction !== null}
              >
                Submit Completion
              </Button>
            ) : null}
            {myAssignment.status === 'pendingReview' ? (
              <p className={styles.hintText}>Submitted and awaiting liaison review.</p>
            ) : null}
            {myAssignment.status === 'archived' ? (
              <p className={styles.hintText}>You have completed this task.</p>
            ) : null}
            {myAssignment.reviewComment ? (
              <p className={styles.commentText}>Latest review comment: {myAssignment.reviewComment}</p>
            ) : null}
            {myAssignment.targetReviewComment ? (
              <p className={styles.commentText}>Receiver review comment: {myAssignment.targetReviewComment}</p>
            ) : null}
          </div>
        )}
      </section>

      <section className={styles.sideSection}>
        <h2 className={styles.sideTitle}>Collaboration Info</h2>
        <dl className={styles.timeList}>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Initiating Unit</dt>
            <dd className={styles.timeValue}>{sourceUnitName}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Receiving Unit</dt>
            <dd className={styles.timeValue}>{targetUnitName}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Current Phase</dt>
            <dd className={styles.timeValue}>{getCollaborationPhaseLabel(task.collaborationPhase)}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Collaboration</dt>
            <dd className={styles.timeValue}>
              {task.collaborationId !== null ? (
                <Link
                  to={'/collaborations/' + String(task.collaborationId)}
                  className={styles.inlineLink}
                >
                  View collaboration details →
                </Link>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>
        {task.collaborationComment ? (
          <p className={styles.commentText}>Receiver comment: {task.collaborationComment}</p>
        ) : null}
      </section>

      <section className={styles.sideSection}>
        <h2 className={styles.sideTitle}>Timeline</h2>
        <dl className={styles.timeList}>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Created</dt>
            <dd className={styles.timeValue}>{formatDateTime(task.createdAt)}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Due Date</dt>
            <dd className={styles.timeValue}>{formatDateTime(task.dueAt)}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Updated</dt>
            <dd className={styles.timeValue}>{formatDateTime(task.updatedAt)}</dd>
          </div>
          <div className={styles.timeItem}>
            <dt className={styles.timeLabel}>Archived</dt>
            <dd className={styles.timeValue}>{formatDateTime(task.archivedAt)}</dd>
          </div>
        </dl>
      </section>
    </aside>
  )
}
