/**
 * 结束协作弹窗：任一方单位管理员可结束 active 状态的协作，可选填写结束原因。
 */

import { useEffect, useState } from 'react'

import { endCollaboration } from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { CollaborationItem } from '../../types/collaboration'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Textarea from '../ui/Textarea'
import { formatCollaborationUnit } from './collaborationUtils'
import styles from './EndCollaborationDialog.module.css'

/** 结束协作弹窗属性。 */
export interface EndCollaborationDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 待结束的协作。 */
  collaboration: CollaborationItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 结束成功回调。 */
  onEnded: (collaboration: CollaborationItem) => void
}

/** 结束协作弹窗。 */
export default function EndCollaborationDialog({
  open,
  collaboration,
  onClose,
  onEnded,
}: EndCollaborationDialogProps) {
  const { showToast } = useToast()
  const [comment, setComment] = useState<string>('')
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 打开弹窗时清空输入。 */
  useEffect(() => {
    if (open) {
      setComment('')
    }
  }, [open, collaboration?.id])

  if (!open || collaboration === null) {
    return null
  }

  /** 提交结束协作。 */
  const handleSubmit = async (): Promise<void> => {
    setSubmitting(true)
    try {
      const updated = await endCollaboration(collaboration.id, comment.trim() === '' ? null : comment.trim())
      onEnded(updated)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to end the collaboration. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={submitting}>
        Cancel
      </Button>
      <Button variant="danger" onClick={() => void handleSubmit()} loading={submitting}>
        Confirm End
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="End Collaboration"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <p className={styles.summaryText}>
          End the collaboration between "{formatCollaborationUnit(collaboration.initiatorUnit)}" and "
          {formatCollaborationUnit(collaboration.targetUnit)}"?
        </p>
        <p className={styles.hintText}>
          After ending, neither party can dispatch new collaboration tasks. Existing tasks continue through their current flow.
        </p>
        <Textarea
          label="End Reason"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          rows={3}
          maxLength={500}
          placeholder="Optional; both parties can view it in the collaboration details"
          disabled={submitting}
        />
      </div>
    </Modal>
  )
}
