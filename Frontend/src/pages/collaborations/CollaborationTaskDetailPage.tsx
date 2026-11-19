/**
 * 协作任务详情页：任务信息、阶段展示、接收方确认/指派、执行进度、双方审核与审核历史。
 *
 * 操作按钮显隐严格依据后端权限标记：canConfirmTask（接收方确认接单）、
 * canTargetReview（接收方审核）、canSourceReview（发起方审核）。
 */

import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getCollaborationTask,
  reviewCollaborationTaskAsSource,
  reviewCollaborationTaskAsTarget,
} from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import { useTaskActions } from '../../hooks/useTaskActions'
import type {
  CollaborationTaskItem,
  ReviewCollaborationTaskPayload,
} from '../../types/collaboration'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import PriorityBadge from '../../components/task/PriorityBadge'
import ReviewHistory from '../../components/task/ReviewHistory'
import StatusBadge from '../../components/task/StatusBadge'
import TaskInfoSection from '../../components/task/TaskInfoSection'
import TaskProgress from '../../components/task/TaskProgress'
import CollaborationPhaseSteps from '../../components/collaboration/CollaborationPhaseSteps'
import CollaborationReviewSection, {
  type CollaborationReviewStage,
} from '../../components/collaboration/CollaborationReviewSection'
import CollaborationTaskConfirmDialog from '../../components/collaboration/CollaborationTaskConfirmDialog'
import CollaborationTaskSidebar from '../../components/collaboration/CollaborationTaskSidebar'
import { getCollaborationPhaseLabel } from '../../components/collaboration/collaborationUtils'
import styles from './CollaborationTaskDetailPage.module.css'

/** 拼接协作任务来源/接收单位名称。 */
function buildUnitName(teamName: string | null, subTeamName: string | null): string {
  if (subTeamName && teamName) {
    return teamName + ' / ' + subTeamName
  }
  if (subTeamName) {
    return subTeamName
  }
  return teamName ?? '—'
}

/** 协作任务详情页。 */
export default function CollaborationTaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const parsedTaskId = Number(taskId)
  const isValidId = Number.isInteger(parsedTaskId) && parsedTaskId > 0
  const { showToast } = useToast()
  const [confirmOpen, setConfirmOpen] = useState<boolean>(false)
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false)

  /** 加载协作任务详情。 */
  const loadTask = useCallback(
    () =>
      isValidId
        ? getCollaborationTask(parsedTaskId)
        : Promise.reject(new Error('Invalid task ID')),
    [isValidId, parsedTaskId],
  )

  const { data: task, loading, error, reload } = useAsync(loadTask, [loadTask])
  const taskActions = useTaskActions(reload)

  /** 接收方确认/拒绝成功：接口返回任务项，重新拉取详情以同步审核记录。 */
  const handleConfirmed = (updated: CollaborationTaskItem): void => {
    setConfirmOpen(false)
    showToast(
      updated.collaborationPhase === 'executing' ? 'Task accepted and assignees assigned' : 'Collaboration task rejected',
      'success',
    )
    reload()
  }

  /** 提交双审核结果。 */
  const handleReview = async (
    stage: CollaborationReviewStage,
    payload: ReviewCollaborationTaskPayload,
  ): Promise<void> => {
    if (!task) {
      return
    }
    setReviewSubmitting(true)
    try {
      if (stage === 'target') {
        await reviewCollaborationTaskAsTarget(task.id, payload)
      } else {
        await reviewCollaborationTaskAsSource(task.id, payload)
      }
      reload()
      showToast(
        payload.approved
          ? stage === 'target'
            ? 'Receiver review approved. The task moves to initiator review.'
            : 'Initiator review approved. The assignee to-do has been archived.'
          : 'Rejected. The task is back in progress.',
        'success',
      )
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to submit the review. Please try again.'), 'error')
    } finally {
      setReviewSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className={styles.loadingBox}>
          <Spinner size="medium" />
          <span>Loading collaboration task...</span>
        </div>
      </div>
    )
  }

  if (error !== null || task === null) {
    return (
      <div className="page-container">
        <EmptyState
          title="Unable to access this collaboration task"
          description={error ?? 'The task does not exist or you do not have permission to view it.'}
          action={
            <Link to="/collaborations">
              <Button variant="secondary">Back to Collaboration Center</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const sourceUnitName = buildUnitName(task.sourceTeamName, task.sourceSubTeamName)
  const targetUnitName = buildUnitName(task.targetTeamName, task.targetSubTeamName)
  const backPath =
    task.collaborationId !== null
      ? '/collaborations/' + String(task.collaborationId)
      : '/tasks'

  return (
    <div className="page-container">
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to={backPath} className={styles.breadcrumbLink}>
          ← {task.collaborationId !== null ? 'Back to Collaboration Details' : 'Back to Task Center'}
        </Link>
      </nav>

      <PageHeader
        title={task.title}
        description={'Initiating unit: ' + sourceUnitName + ' · Receiving unit: ' + targetUnitName}
        actions={
          <div className={styles.headerBadges}>
            <PriorityBadge priority={task.priority} />
            <StatusBadge status={task.status} kind="task" />
            <Badge variant="outline" size="small">
              {getCollaborationPhaseLabel(task.collaborationPhase)}
            </Badge>
          </div>
        }
      />

      <div className={styles.detailLayout}>
        <div className={styles.mainColumn}>
          <TaskInfoSection task={task} />
          <CollaborationPhaseSteps phase={task.collaborationPhase} archived={task.status === 'archived'} />
          <TaskProgress task={task} />
          <CollaborationReviewSection
            task={task}
            submitting={reviewSubmitting}
            onSubmit={handleReview}
          />
          <ReviewHistory reviews={task.reviews} />
        </div>

        <CollaborationTaskSidebar
          task={task}
          sourceUnitName={sourceUnitName}
          targetUnitName={targetUnitName}
          pendingAction={taskActions.pendingAction}
          onAccept={() => void taskActions.accept(task.id)}
          onDecline={() => void taskActions.decline(task.id)}
          onSubmit={() => void taskActions.submit(task.id)}
          onOpenConfirm={() => setConfirmOpen(true)}
        />
      </div>

      <CollaborationTaskConfirmDialog
        open={confirmOpen}
        task={task}
        onClose={() => setConfirmOpen(false)}
        onConfirmed={handleConfirmed}
      />
    </div>
  )
}