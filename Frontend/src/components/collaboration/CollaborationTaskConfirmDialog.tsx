/**
 * 协作任务确认弹窗：接收方对接人确认接单并指派执行人，或拒绝任务。
 *
 * 指派候选来自接收单位成员（GET /collaborations/units/members）；
 * 确认时至少选择 1 名执行人，拒绝时必须填写原因。
 */

import { useEffect, useState } from 'react'

import { confirmCollaborationTask } from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { CollaborationTaskDetail, CollaborationTaskItem } from '../../types/collaboration'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import RadioGroup from '../ui/RadioGroup'
import Textarea from '../ui/Textarea'
import UnitMemberPicker from './UnitMemberPicker'
import useUnitMembers from './useUnitMembers'
import styles from './CollaborationTaskConfirmDialog.module.css'

/** 协作任务确认弹窗属性。 */
export interface CollaborationTaskConfirmDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 待确认的协作任务。 */
  task: CollaborationTaskDetail | null
  /** 关闭回调。 */
  onClose: () => void
  /** 处理成功回调。 */
  onConfirmed: (task: CollaborationTaskItem) => void
}

/** 处理方式。 */
type Decision = 'approve' | 'reject'

/** 处理方式选项。 */
const DECISION_OPTIONS = [
  { value: 'approve', label: 'Accept Task', description: 'The task enters execution after assignees are selected' },
  { value: 'reject', label: 'Reject Task', description: 'The task will be cancelled. A rejection reason is required.' },
]

/** 协作任务确认弹窗。 */
export default function CollaborationTaskConfirmDialog({
  open,
  task,
  onClose,
  onConfirmed,
}: CollaborationTaskConfirmDialogProps) {
  const { showToast } = useToast()
  const [decision, setDecision] = useState<Decision>('approve')
  const [assigneeUserIds, setAssigneeUserIds] = useState<number[]>([])
  const [comment, setComment] = useState<string>('')
  const [assigneeError, setAssigneeError] = useState<string | undefined>(undefined)
  const [commentError, setCommentError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const unitMembersState = useUnitMembers(
    task?.targetTeamId ?? null,
    task?.targetSubTeamId ?? null,
    open && task !== null,
  )

  /** 打开弹窗或切换任务时重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setDecision('approve')
    setAssigneeUserIds([])
    setComment('')
    setAssigneeError(undefined)
    setCommentError(undefined)
  }, [open, task?.id])

  if (!open || task === null) {
    return null
  }

  const targetUnitName = task.targetSubTeamName ?? task.targetTeamName ?? 'Receiving Unit'

  /** 提交确认结果。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedComment = comment.trim()
    let hasError = false
    if (decision === 'approve' && assigneeUserIds.length === 0) {
      setAssigneeError('Assign at least one assignee when accepting the task')
      hasError = true
    }
    if (decision === 'reject' && trimmedComment === '') {
      setCommentError('Enter a reason when rejecting the task')
      hasError = true
    }
    if (hasError) {
      return
    }
    setSubmitting(true)
    try {
      const updated = await confirmCollaborationTask(task.id, {
        approved: decision === 'approve',
        assigneeUserIds: decision === 'approve' ? assigneeUserIds : undefined,
        comment: trimmedComment === '' ? null : trimmedComment,
      })
      onConfirmed(updated)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to process the collaboration task. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={submitting}>
        Cancel
      </Button>
      <Button
        variant={decision === 'reject' ? 'danger' : 'primary'}
        onClick={() => void handleSubmit()}
        loading={submitting}
      >
        {decision === 'reject' ? 'Confirm Rejection' : 'Confirm Acceptance'}
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="Process Collaboration Task"
      size="large"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <p className={styles.taskTitle}>{task.title}</p>
        <p className={styles.unitHint}>Receiving unit: {targetUnitName}</p>

        <RadioGroup
          value={decision}
          onChange={(value) => setDecision(value === 'reject' ? 'reject' : 'approve')}
          options={DECISION_OPTIONS}
          disabled={submitting}
        />

        {decision === 'approve' ? (
          <UnitMemberPicker
            label="Assign Assignees (multi-select)"
            members={unitMembersState.data ?? []}
            selectedUserIds={assigneeUserIds}
            onChange={(userIds) => {
              setAssigneeUserIds(userIds)
              setAssigneeError(undefined)
            }}
            loading={unitMembersState.loading}
            disabled={submitting}
            error={assigneeError ?? (unitMembersState.error ?? undefined)}
            emptyText="The receiving unit has no members, so assignees cannot be selected"
          />
        ) : null}

        <Textarea
          label={decision === 'approve' ? 'Acceptance Comment' : 'Rejection Reason'}
          value={comment}
          onChange={(event) => {
            setComment(event.target.value)
            setCommentError(undefined)
          }}
          rows={3}
          maxLength={500}
          placeholder={decision === 'approve' ? 'Optional; visible to the initiator' : 'Required; explain the rejection reason'}
          disabled={submitting}
          error={commentError}
        />
      </div>
    </Modal>
  )
}