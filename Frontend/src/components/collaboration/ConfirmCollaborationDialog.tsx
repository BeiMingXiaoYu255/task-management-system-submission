/**
 * 处理协作申请弹窗：接收方管理员确认（并指定接收方对接人）或拒绝（填写原因）。
 *
 * 对接人候选通过 GET /collaborations/units/members 拉取，必须是接收方单位成员；
 * 拒绝必须填写原因，便于发起方了解未通过原因。
 */

import { useEffect, useState } from 'react'

import { confirmCollaboration } from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { CollaborationItem } from '../../types/collaboration'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import RadioGroup from '../ui/RadioGroup'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import useUnitMembers from './useUnitMembers'
import { formatCollaborationUnit } from './collaborationUtils'
import styles from './ConfirmCollaborationDialog.module.css'

/** 处理协作申请弹窗属性。 */
export interface ConfirmCollaborationDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 待处理的协作申请。 */
  collaboration: CollaborationItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 处理成功回调。 */
  onConfirmed: (collaboration: CollaborationItem) => void
}

/** 处理方式。 */
type Decision = 'approve' | 'reject'

/** 处理方式选项。 */
const DECISION_OPTIONS = [
  { value: 'approve', label: 'Confirm Collaboration', description: 'The collaboration becomes active and collaboration tasks can be dispatched' },
  { value: 'reject', label: 'Reject Request', description: 'The request will be closed. A rejection reason is required.' },
]

/** 处理协作申请弹窗。 */
export default function ConfirmCollaborationDialog({
  open,
  collaboration,
  onClose,
  onConfirmed,
}: ConfirmCollaborationDialogProps) {
  const { showToast } = useToast()
  const [decision, setDecision] = useState<Decision>('approve')
  const [liaisonUserId, setLiaisonUserId] = useState<number>(0)
  const [comment, setComment] = useState<string>('')
  const [liaisonError, setLiaisonError] = useState<string | undefined>(undefined)
  const [commentError, setCommentError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const targetUnit = collaboration?.targetUnit ?? null
  const unitMembersState = useUnitMembers(
    targetUnit?.teamId ?? null,
    targetUnit?.subTeamId ?? null,
    open && targetUnit !== null,
  )

  /** 打开弹窗或切换申请时重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setDecision('approve')
    setLiaisonUserId(0)
    setComment('')
    setLiaisonError(undefined)
    setCommentError(undefined)
  }, [open, collaboration?.id])

  if (!open || collaboration === null) {
    return null
  }

  /** 对接人选项。 */
  const liaisonOptions = (unitMembersState.data ?? []).map((member) => ({
    value: member.userId,
    label: member.nickname + ' (' + member.levelName + ')',
  }))

  /** 提交处理结果。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedComment = comment.trim()
    let hasError = false
    if (decision === 'approve' && liaisonUserId <= 0) {
      setLiaisonError('A receiver liaison is required when confirming the collaboration')
      hasError = true
    }
    if (decision === 'reject' && trimmedComment === '') {
      setCommentError('Enter a rejection reason when rejecting the request')
      hasError = true
    }
    if (hasError) {
      return
    }
    setSubmitting(true)
    try {
      const updated = await confirmCollaboration(collaboration.id, {
        approved: decision === 'approve',
        targetLiaisonUserId: decision === 'approve' ? liaisonUserId : null,
        comment: trimmedComment === '' ? null : trimmedComment,
      })
      onConfirmed(updated)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to process the collaboration request. Please try again.'), 'error')
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
        {decision === 'reject' ? 'Confirm Rejection' : 'Confirm Collaboration'}
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="Process Collaboration Request"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <div className={styles.summary}>
          <span className={styles.unitName}>{formatCollaborationUnit(collaboration.initiatorUnit)}</span>
          <span className={styles.arrow} aria-hidden="true">
            →
          </span>
          <span className={styles.unitName}>{formatCollaborationUnit(collaboration.targetUnit)}</span>
        </div>
        <p className={styles.metaText}>Applicant: {collaboration.createdByName}</p>
        {collaboration.message ? (
          <p className={styles.messageText}>Request note: {collaboration.message}</p>
        ) : null}

        <RadioGroup
          value={decision}
          onChange={(value) => {
            setDecision(value === 'reject' ? 'reject' : 'approve')
          }}
          options={DECISION_OPTIONS}
          disabled={submitting}
        />

        {decision === 'approve' ? (
          <Select
            label="Receiver Liaison"
            value={liaisonUserId}
            onChange={(value) => {
              setLiaisonUserId(Number(value))
              setLiaisonError(undefined)
            }}
            options={liaisonOptions}
            placeholder="Select a receiver liaison"
            disabled={submitting}
            error={liaisonError ?? (unitMembersState.error ?? undefined)}
            hint={unitMembersState.loading ? 'Loading members...' : 'The liaison confirms collaboration tasks and assigns assignees'}
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
          placeholder={
            decision === 'approve' ? 'Optional; both parties can view it in the collaboration details' : 'Required; explain the rejection reason'
          }
          disabled={submitting}
          error={commentError}
        />
      </div>
    </Modal>
  )
}
