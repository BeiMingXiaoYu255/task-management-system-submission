/**
 * 协作任务双审核面板：接收方审核与发起方审核共用。
 *
 * 仅当后端返回 canTargetReview / canSourceReview 为 true 时展示对应区块；
 * 每个执行人独立审核，驳回必须填写意见，提交成功后由父级回写最新任务详情。
 */

import { useState } from 'react'

import type {
  CollaborationTaskDetail,
  ReviewCollaborationTaskPayload,
} from '../../types/collaboration'
import type { TaskAssignmentItem } from '../../types/task'
import { formatDateTime } from '../../utils/formatUtils'
import Avatar from '../ui/Avatar'
import Button from '../ui/Button'
import Textarea from '../ui/Textarea'
import styles from './CollaborationReviewSection.module.css'

/** 审核阶段。 */
export type CollaborationReviewStage = 'target' | 'source'

/** 协作任务双审核面板属性。 */
export interface CollaborationReviewSectionProps {
  /** 协作任务详情。 */
  task: CollaborationTaskDetail
  /** 审核请求是否进行中。 */
  submitting: boolean
  /** 提交审核结果回调。 */
  onSubmit: (stage: CollaborationReviewStage, payload: ReviewCollaborationTaskPayload) => Promise<void>
}

/** 判断某个执行人提交是否属于指定审核阶段。 */
function isAssignmentInStage(
  assignment: TaskAssignmentItem,
  stage: CollaborationReviewStage,
  phase: string | null,
): boolean {
  if (assignment.status !== 'pendingReview') {
    return false
  }
  if (assignment.reviewStage !== null) {
    return assignment.reviewStage === stage
  }
  const expectedPhase = stage === 'target' ? 'targetReview' : 'sourceReview'
  return phase === expectedPhase
}

/** 协作任务双审核面板。 */
export default function CollaborationReviewSection({
  task,
  submitting,
  onSubmit,
}: CollaborationReviewSectionProps) {
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({})
  const [commentErrors, setCommentErrors] = useState<Record<string, string>>({})

  const stageConfigs: { stage: CollaborationReviewStage; title: string; description: string }[] = []
  if (task.canTargetReview) {
    stageConfigs.push({
      stage: 'target',
      title: 'Receiver Review',
      description: 'As the receiver liaison, review the work submitted by assignees. Approval moves the task to the initiator review.',
    })
  }
  if (task.canSourceReview) {
    stageConfigs.push({
      stage: 'source',
      title: 'Initiator Review',
      description: "As the initiator publisher, perform the final acceptance review. Approval archives the assignee's to-do.",
    })
  }

  if (stageConfigs.length === 0) {
    return null
  }

  /** 更新审核意见草稿并清除对应错误。 */
  const updateDraft = (draftKey: string, comment: string): void => {
    setCommentDrafts((previousDrafts) => ({ ...previousDrafts, [draftKey]: comment }))
    setCommentErrors((previousErrors) => {
      if (!previousErrors[draftKey]) {
        return previousErrors
      }
      const nextErrors = { ...previousErrors }
      delete nextErrors[draftKey]
      return nextErrors
    })
  }

  /** 提交某个执行人的审核结果。 */
  const handleReview = async (
    stage: CollaborationReviewStage,
    assignmentUserId: number,
    approved: boolean,
  ): Promise<void> => {
    const draftKey = stage + '-' + String(assignmentUserId)
    const comment = (commentDrafts[draftKey] ?? '').trim()
    if (!approved && comment === '') {
      setCommentErrors((previousErrors) => ({
        ...previousErrors,
        [draftKey]: 'Enter review comments when rejecting and explain what needs to change',
      }))
      return
    }
    await onSubmit(stage, {
      assignmentUserId,
      approved,
      comment: comment === '' ? null : comment,
    })
    setCommentDrafts((previousDrafts) => {
      const nextDrafts = { ...previousDrafts }
      delete nextDrafts[draftKey]
      return nextDrafts
    })
  }

  return (
    <div className={styles.reviewWrapper}>
      {stageConfigs.map((stageConfig) => {
        const pendingAssignments = task.assignments.filter((assignment) =>
          isAssignmentInStage(assignment, stageConfig.stage, task.collaborationPhase),
        )
        return (
          <section key={stageConfig.stage} className={styles.reviewSection}>
            <header className={styles.sectionHeader}>
              <div>
                <h3 className={styles.sectionTitle}>{stageConfig.title}</h3>
                <p className={styles.sectionDescription}>{stageConfig.description}</p>
              </div>
              <span className={styles.sectionHint}>{pendingAssignments.length} submissions</span>
            </header>
            {pendingAssignments.length === 0 ? (
              <p className={styles.emptyHint}>There are no submissions waiting for your review.</p>
            ) : (
              <ul className={styles.reviewList}>
                {pendingAssignments.map((assignment) => {
                  const draftKey = stageConfig.stage + '-' + String(assignment.userId)
                  return (
                    <li key={assignment.id} className={styles.reviewItem}>
                      <div className={styles.memberRow}>
                        <Avatar
                          name={assignment.nickname}
                          src={assignment.avatar ?? undefined}
                          size="small"
                        />
                        <div className={styles.memberInfo}>
                          <span className={styles.memberName}>{assignment.nickname}</span>
                          <span className={styles.memberMeta}>
                            Submitted: {formatDateTime(assignment.submittedAt)}
                          </span>
                        </div>
                      </div>
                      <Textarea
                        label="Review Comments"
                        value={commentDrafts[draftKey] ?? ''}
                        onChange={(event) => updateDraft(draftKey, event.target.value)}
                        placeholder="Optional when approving; required when rejecting. Explain what needs to change"
                        rows={2}
                        maxLength={500}
                        error={commentErrors[draftKey]}
                        disabled={submitting}
                      />
                      <div className={styles.actionRow}>
                        <Button
                          size="small"
                          loading={submitting}
                          onClick={() => void handleReview(stageConfig.stage, assignment.userId, true)}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          size="small"
                          disabled={submitting}
                          onClick={() => void handleReview(stageConfig.stage, assignment.userId, false)}
                        >
                          Reject
                        </Button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        )
      })}
    </div>
  )
}
