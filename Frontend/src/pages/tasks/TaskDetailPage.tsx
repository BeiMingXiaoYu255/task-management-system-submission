/**
 * 任务详情页：任务信息、执行进度、当前用户操作（接受/拒绝/提交完成）、
 * 发布者审核（通过/驳回+意见）与审核历史。
 *
 * 数据流：页面加载任务详情后，所有操作都返回最新 TaskDetail，
 * 通过 useTaskActions 的 onChanged 直接写入详情数据，避免整页重新加载。
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getTask } from '../../api/taskApi'
import { useToast } from '../../context/ToastContext'
import { useAsync } from '../../hooks/useAsync'
import { useTaskActions } from '../../hooks/useTaskActions'
import type { ReviewTaskPayload, TaskDetail } from '../../types/task'
import { formatDateTime } from '../../utils/formatUtils'
import Button from '../../components/ui/Button'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import PriorityBadge from '../../components/task/PriorityBadge'
import ReviewHistory from '../../components/task/ReviewHistory'
import ReviewPanel from '../../components/task/ReviewPanel'
import StatusBadge from '../../components/task/StatusBadge'
import TaskInfoSection from '../../components/task/TaskInfoSection'
import TaskProgress from '../../components/task/TaskProgress'
import ManualAssignDialog from '../../components/collaboration/ManualAssignDialog'
import styles from './TaskDetailPage.module.css'

/** 任务详情页。 */
export default function TaskDetailPage() {
  const { teamId, taskId } = useParams<{ teamId: string; taskId: string }>()
  const parsedTaskId = Number(taskId)
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [cancelDialogOpen, setCancelDialogOpen] = useState<boolean>(false)
  const [manualAssignOpen, setManualAssignOpen] = useState<boolean>(false)

  /** 加载任务详情：先校验路由参数。 */
  const loadTask = useCallback((): Promise<TaskDetail> => {
    if (!Number.isInteger(parsedTaskId) || parsedTaskId <= 0) {
      return Promise.reject(new Error('Invalid task ID'))
    }
    return getTask(parsedTaskId)
  }, [parsedTaskId])

  const { data: task, loading, error, setData } = useAsync(loadTask, [loadTask])
  const taskActions = useTaskActions((updatedTask) => setData(updatedTask))
  const backTeamId = task?.teamId ?? Number(teamId)

  /** 协作任务统一跳转到协作任务详情页处理双审核与接单流程。 */
  useEffect(() => {
    if (task !== null && task.collaborationId !== null) {
      navigate('/collaboration-tasks/' + task.id, { replace: true })
    }
  }, [task, navigate])

  /** 发布者审核回调：hooks 统一处理成功提示与数据回写。 */
  const handleReview = async (payload: ReviewTaskPayload): Promise<void> => {
    if (!task) {
      return
    }
    await taskActions.review(task.id, payload)
  }

  /** 确认取消任务。 */
  const handleConfirmCancel = async (): Promise<void> => {
    if (!task) {
      return
    }
    await taskActions.cancel(task.id)
    setCancelDialogOpen(false)
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading task...</span>
        </div>
      </div>
    )
  }

  if (task !== null && task.collaborationId !== null) {
    return (
      <div className="page-container">
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Redirecting to collaboration task details...</span>
        </div>
      </div>
    )
  }

  if (error !== null || task === null) {
    return (
      <div className="page-container">
        <EmptyState
          title="Unable to access this task"
          description={error ?? 'The task does not exist or you do not have access.'}
          action={
            <Link to={'/teams/' + String(backTeamId)}>
              <Button variant="secondary">Back to Team</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const myAssignment = task.myAssignment
  const canCancel = task.canEdit && task.status !== 'archived' && task.status !== 'cancelled'
  const canManualAssign =
    task.canAssign && task.status !== 'archived' && task.status !== 'cancelled'

  return (
    <div className="page-container">
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to={'/teams/' + task.teamId} className={styles.breadcrumbLink}>
          ← Back to Team
        </Link>
      </nav>

      <PageHeader
        title={task.title}
        description={
          'Team: ' + task.teamName + ' · Publisher: ' + task.createdByName
        }
        actions={
          <div className={styles.headerBadges}>
            <PriorityBadge priority={task.priority} />
            <StatusBadge status={task.status} kind="task" />
          </div>
        }
      />

      <div className={styles.detailLayout}>
        <div className={styles.mainColumn}>
          <TaskInfoSection task={task} />
          <TaskProgress task={task} />
          <ReviewPanel
            task={task}
            submitting={taskActions.pendingAction === 'review'}
            onSubmit={handleReview}
          />
          <ReviewHistory reviews={task.reviews} />
        </div>

        <aside className={styles.sideColumn}>
          <section className={styles.sideSection}>
            <h2 className={styles.sideTitle}>My Actions</h2>
            {myAssignment === null ? (
              <p className={styles.hintText}>You are not an assignee on this task. You can view progress and review history.</p>
            ) : (
              <div className={styles.myAssignmentBlock}>
                <div className={styles.myAssignmentRow}>
                  <span className={styles.hintText}>My Status</span>
                  <StatusBadge status={myAssignment.status} kind="assignment" />
                </div>
                {myAssignment.status === 'pendingAcceptance' ? (
                  <div className={styles.actionRow}>
                    <Button
                      onClick={() => void taskActions.accept(task.id)}
                      loading={taskActions.pendingAction === 'accept'}
                      disabled={taskActions.pendingAction !== null}
                    >
                      Accept Task
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => void taskActions.decline(task.id)}
                      loading={taskActions.pendingAction === 'decline'}
                      disabled={taskActions.pendingAction !== null}
                    >
                      Reject Task
                    </Button>
                  </div>
                ) : null}
                {myAssignment.status === 'inProgress' ? (
                  <Button
                    onClick={() => void taskActions.submit(task.id)}
                    loading={taskActions.pendingAction === 'submit'}
                    disabled={taskActions.pendingAction !== null}
                  >
                    Submit Completion
                  </Button>
                ) : null}
                {myAssignment.status === 'pendingReview' ? (
                  <p className={styles.hintText}>Submitted. Waiting for the publisher to review.</p>
                ) : null}
                {myAssignment.status === 'archived' ? (
                  <p className={styles.hintText}>The task is archived. You have completed it.</p>
                ) : null}
                {myAssignment.reviewComment ? (
                  <p className={styles.reviewCommentText}>
                    Latest review comment: {myAssignment.reviewComment}
                  </p>
                ) : null}
                {myAssignment.submittedAt ? (
                  <p className={styles.hintText}>Submitted: {formatDateTime(myAssignment.submittedAt)}</p>
                ) : null}
              </div>
            )}
          </section>

          {canManualAssign ? (
            <section className={styles.sideSection}>
              <h2 className={styles.sideTitle}>Assign Assignee</h2>
              <p className={styles.hintText}>
                This task has no assignee yet (AI auto-assignment may not have matched). You can manually assign a team member.
              </p>
              <Button onClick={() => setManualAssignOpen(true)}>Assign Assignee</Button>
            </section>
          ) : null}

          {canCancel ? (
            <section className={styles.sideSection}>
              <h2 className={styles.sideTitle}>Publisher Actions</h2>
              <p className={styles.hintText}>Canceling the task marks it and all its to-dos as canceled.</p>
              <Button variant="danger" onClick={() => setCancelDialogOpen(true)}>
                Cancel Task
              </Button>
            </section>
          ) : null}

          <section className={styles.sideSection}>
            <h2 className={styles.sideTitle}>Time Information</h2>
            <dl className={styles.timeList}>
              <div className={styles.timeItem}>
                <dt className={styles.timeLabel}>Created at</dt>
                <dd className={styles.timeValue}>{formatDateTime(task.createdAt)}</dd>
              </div>
              <div className={styles.timeItem}>
                <dt className={styles.timeLabel}>Updated at</dt>
                <dd className={styles.timeValue}>{formatDateTime(task.updatedAt)}</dd>
              </div>
              <div className={styles.timeItem}>
                <dt className={styles.timeLabel}>Archived at</dt>
                <dd className={styles.timeValue}>{formatDateTime(task.archivedAt)}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>

      <ManualAssignDialog
        open={manualAssignOpen}
        task={task}
        onClose={() => setManualAssignOpen(false)}
        onAssigned={(updatedTask) => {
          setData(updatedTask)
          setManualAssignOpen(false)
          showToast('Assignee assigned', 'success')
        }}
      />

      <ConfirmDialog
        open={cancelDialogOpen}
        title="Cancel Task"
        description="Cancel this task? Assignees will no longer be able to work on it, and the task cannot be restored."
        confirmText="Confirm Cancellation"
        danger
        loading={taskActions.pendingAction === 'cancel'}
        onConfirm={() => void handleConfirmCancel()}
        onCancel={() => {
          if (taskActions.pendingAction !== 'cancel') {
            setCancelDialogOpen(false)
          }
        }}
      />
    </div>
  )
}