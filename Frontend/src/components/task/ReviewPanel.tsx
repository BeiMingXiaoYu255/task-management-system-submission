/**
 * 任务审核面板：发布者对“待审核”的执行人提交进行通过/驳回。
 *
 * 交互约束：
 * 1. 驳回必须填写评审意见，便于执行人修改；通过时意见可选；
 * 2. 每个执行人独立审核，提交期间禁用全部按钮，避免重复请求；
 * 3. 审核成功后由父级回拉详情，待审核列表自动刷新。
 */

import { useState } from 'react'

import type { TaskDetail } from '../../types/task'
import { formatDateTime } from '../../utils/formatUtils'
import Avatar from '../ui/Avatar'
import Button from '../ui/Button'
import Textarea from '../ui/Textarea'
import styles from './ReviewPanel.module.css'

/** ReviewPanel 组件属性。 */
export interface ReviewPanelProps {
  /** 任务详情数据。 */
  task: TaskDetail
  /** 审核请求是否进行中。 */
  submitting: boolean
  /** 提交审核回调；驳回时 comment 一定非空。 */
  onSubmit: (payload: {
    assignmentUserId: number
    approved: boolean
    comment: string | null
  }) => Promise<void>
}

/** 任务审核面板。 */
export default function ReviewPanel({ task, submitting, onSubmit }: ReviewPanelProps) {
  const [commentDrafts, setCommentDrafts] = useState<Record<number, string>>({})
  const [commentErrors, setCommentErrors] = useState<Record<number, string>>({})

  const pendingReviewAssignments = task.assignments.filter(
    (assignment) => assignment.status === 'pendingReview',
  )

  /** 更新某位执行人的评审意见草稿。 */
  const updateCommentDraft = (userId: number, comment: string): void => {
    setCommentDrafts((previousDrafts) => ({ ...previousDrafts, [userId]: comment }))
    setCommentErrors((previousErrors) => {
      if (!previousErrors[userId]) {
        return previousErrors
      }
      const nextErrors = { ...previousErrors }
      delete nextErrors[userId]
      return nextErrors
    })
  }

  /** 提交审核结果。 */
  const handleReview = async (userId: number, approved: boolean): Promise<void> => {
    const comment = (commentDrafts[userId] ?? '').trim()
    if (!approved && comment.length === 0) {
      setCommentErrors((previousErrors) => ({
        ...previousErrors,
        [userId]: 'When rejecting, add a review comment explaining what needs to change.',
      }))
      return
    }
    await onSubmit({
      assignmentUserId: userId,
      approved,
      comment: comment.length === 0 ? null : comment,
    })
    setCommentDrafts((previousDrafts) => {
      const nextDrafts = { ...previousDrafts }
      delete nextDrafts[userId]
      return nextDrafts
    })
  }

  // 协作任务的双审核由协作任务详情页处理，这里只负责普通任务
  if (!task.canReview || task.collaborationId !== null) {
    return null
  }

  return (
    <section className={styles.reviewSection}>
      <header className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Pending My Review</h3>
        <span className={styles.sectionHint}>{pendingReviewAssignments.length} submissions</span>
      </header>
      {pendingReviewAssignments.length === 0 ? (
        <p className={styles.emptyHint}>No submissions to review right now.</p>
      ) : (
        <ul className={styles.reviewList}>
          {pendingReviewAssignments.map((assignment) => (
            <li key={assignment.id} className={styles.reviewItem}>
              <div className={styles.memberRow}>
                <Avatar name={assignment.nickname} src={assignment.avatar ?? undefined} size="small" />
                <div className={styles.memberInfo}>
                  <span className={styles.memberName}>{assignment.nickname}</span>
                  <span className={styles.memberMeta}>
                    Submitted: {formatDateTime(assignment.submittedAt)}
                  </span>
                  {assignment.reviewStage !== null ? (
                    <span className={styles.stageHint}>
                      Review stage: 
                      {assignment.reviewStage === 'target' ? 'Receiver Review' : 'Initiator Review'}
                    </span>
                  ) : null}
                </div>
              </div>
              <Textarea
                label="Review Comment"
                value={commentDrafts[assignment.userId] ?? assignment.reviewComment ?? ''}
                onChange={(event) => updateCommentDraft(assignment.userId, event.target.value)}
                placeholder="Optional when approving; required when rejecting. Explain what needs to change."
                rows={2}
                maxLength={500}
                error={commentErrors[assignment.userId]}
                disabled={submitting}
              />
              <div className={styles.actionRow}>
                <Button
                  size="small"
                  loading={submitting}
                  onClick={() => void handleReview(assignment.userId, true)}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  size="small"
                  disabled={submitting}
                  onClick={() => void handleReview(assignment.userId, false)}
                >
                  Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}