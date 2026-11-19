/**
 * 手动指派执行人弹窗：用于 AI 自动分配失败或管理员改派的无执行人任务。
 *
 * 候选人来自团队成员列表；提交后调用 POST /tasks/{taskId}/assignments 生成 manual 来源待办。
 */

import { useEffect, useState } from 'react'

import { assignTaskMembers } from '../../api/taskApi'
import { listTeamMembers } from '../../api/teamApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import type { TaskDetail } from '../../types/task'
import type { TeamMemberItem } from '../../types/team'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import UnitMemberPicker from './UnitMemberPicker'
import styles from './ManualAssignDialog.module.css'

/** 手动指派执行人弹窗属性。 */
export interface ManualAssignDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 待指派任务。 */
  task: TaskDetail | null
  /** 关闭回调。 */
  onClose: () => void
  /** 指派成功回调。 */
  onAssigned: (task: TaskDetail) => void
}

/** 手动指派执行人弹窗。 */
export default function ManualAssignDialog({
  open,
  task,
  onClose,
  onAssigned,
}: ManualAssignDialogProps) {
  const { showToast } = useToast()
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([])
  const [selectionError, setSelectionError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 团队成员候选。 */
  const membersState = useAsync<TeamMemberItem[]>(
    () => (open && task !== null ? listTeamMembers(task.teamId) : Promise.resolve([])),
    [open, task?.teamId],
  )

  /** 打开弹窗时清空选择。 */
  useEffect(() => {
    if (open) {
      setSelectedUserIds([])
      setSelectionError(undefined)
    }
  }, [open, task?.id])

  if (!open || task === null) {
    return null
  }

  const pickableMembers = (membersState.data ?? []).map((member) => ({
    userId: member.userId,
    username: member.username,
    nickname: member.nickname,
    avatar: member.avatar,
    levelName: member.levelName,
  }))

  /** 提交手动指派。 */
  const handleSubmit = async (): Promise<void> => {
    if (selectedUserIds.length === 0) {
      setSelectionError('Select at least one assignee')
      return
    }
    setSubmitting(true)
    try {
      const updated = await assignTaskMembers(task.id, { userIds: selectedUserIds })
      onAssigned(updated)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Assignment failed. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onClose} disabled={submitting}>
        Cancel
      </Button>
      <Button onClick={() => void handleSubmit()} loading={submitting}>
        Confirm Assignment
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="Assign Assignees Manually"
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
        <p className={styles.hintText}>
          This task currently has no assignees (manual assignment is required when AI auto-assignment finds no match). Members receive a to-do notification after assignment.
        </p>
        <UnitMemberPicker
          label="Select Assignees (multi-select)"
          members={pickableMembers}
          selectedUserIds={selectedUserIds}
          onChange={(userIds) => {
            setSelectedUserIds(userIds)
            setSelectionError(undefined)
          }}
          loading={membersState.loading}
          disabled={submitting}
          error={selectionError ?? (membersState.error ?? undefined)}
          emptyText="No other team members are available for assignment"
        />
      </div>
    </Modal>
  )
}
