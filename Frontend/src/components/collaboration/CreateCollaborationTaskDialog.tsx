/**
 * 新建协作任务弹窗：填写标题、描述、优先级、截止时间与接受方式。
 *
 * 协作任务不选择分配对象：接收方对接人确认接单时再从接收单位成员中指派执行人。
 */

import { useEffect, useState } from 'react'

import { createCollaborationTask } from '../../api/collaborationApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import type { AcceptanceMode, TaskPriority } from '../../types/common'
import type {
  CollaborationItem,
  CollaborationTaskItem,
  CreateCollaborationTaskPayload,
} from '../../types/collaboration'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import RadioGroup from '../ui/RadioGroup'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import { formatCollaborationUnit } from './collaborationUtils'
import styles from './CreateCollaborationTaskDialog.module.css'

/** 新建协作任务弹窗属性。 */
export interface CreateCollaborationTaskDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 所属协作关系。 */
  collaboration: CollaborationItem | null
  /** 关闭回调。 */
  onClose: () => void
  /** 创建成功回调。 */
  onCreated: (task: CollaborationTaskItem) => void
}

/** 优先级选项。 */
const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

/** 接受方式选项。 */
const ACCEPTANCE_OPTIONS = [
  { value: 'mandatory', label: 'Mandatory Acceptance', description: 'Assignees cannot decline; the task enters execution immediately after assignment' },
  { value: 'optional', label: 'Optional Acceptance', description: 'Assignees can decline; the liaison reassigns if declined' },
]

/** 把 datetime-local 输入值转换为接口时间字符串。 */
function toApiDateTimeValue(value: string): string | null {
  const trimmedValue = value.trim()
  if (trimmedValue === '') {
    return null
  }
  return trimmedValue.length === 16 ? trimmedValue + ':00' : trimmedValue
}

/** 新建协作任务弹窗。 */
export default function CreateCollaborationTaskDialog({
  open,
  collaboration,
  onClose,
  onCreated,
}: CreateCollaborationTaskDialogProps) {
  const { showToast } = useToast()
  const [title, setTitle] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [priority, setPriority] = useState<string>('medium')
  const [dueAt, setDueAt] = useState<string>('')
  const [acceptanceMode, setAcceptanceMode] = useState<AcceptanceMode>('mandatory')
  const [titleError, setTitleError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 打开弹窗时重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setTitle('')
    setDescription('')
    setPriority('medium')
    setDueAt('')
    setAcceptanceMode('mandatory')
    setTitleError(undefined)
  }, [open, collaboration?.id])

  if (!open || collaboration === null) {
    return null
  }

  /** 提交新建协作任务。 */
  const handleSubmit = async (): Promise<void> => {
    const trimmedTitle = title.trim()
    if (trimmedTitle.length < 2 || trimmedTitle.length > 200) {
      setTitleError('Task title must be 2-200 characters')
      return
    }
    const payload: CreateCollaborationTaskPayload = {
      title: trimmedTitle,
      description: description.trim() === '' ? null : description.trim(),
      priority: priority as TaskPriority,
      dueAt: toApiDateTimeValue(dueAt),
      acceptanceMode,
    }
    setSubmitting(true)
    try {
      const created = await createCollaborationTask(collaboration.id, payload)
      onCreated(created)
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to create the collaboration task. Please try again.'), 'error')
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
        Create Task
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title="New Collaboration Task"
      size="large"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onClose()
        }
      }}
    >
      <div className={styles.body}>
        <p className={styles.unitHint}>
          Collaboration units: {formatCollaborationUnit(collaboration.initiatorUnit)} →{' '}
          {formatCollaborationUnit(collaboration.targetUnit)}
        </p>
        <Input
          label="Task Title"
          value={title}
          onChange={(event) => {
            setTitle(event.target.value)
            setTitleError(undefined)
          }}
          placeholder="Enter a task title (2-200 characters)"
          maxLength={200}
          error={titleError}
          disabled={submitting}
          autoFocus
        />
        <Textarea
          label="Task Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={4}
          maxLength={2000}
          placeholder="Describe the task goals, deliverables, and notes (optional)"
          disabled={submitting}
        />
        <Select
          label="Priority"
          value={priority}
          onChange={(value) => setPriority(String(value))}
          options={PRIORITY_OPTIONS}
          disabled={submitting}
        />
        <Input
          label="Due Date"
          type="datetime-local"
          value={dueAt}
          onChange={(event) => setDueAt(event.target.value)}
          hint="Optional; leave blank for no due date"
          disabled={submitting}
        />
        <div className={styles.fieldBlock}>
          <span className={styles.fieldLabel}>Acceptance Mode</span>
          <RadioGroup
            value={acceptanceMode}
            onChange={(value) => setAcceptanceMode(value as AcceptanceMode)}
            options={ACCEPTANCE_OPTIONS}
            disabled={submitting}
          />
        </div>
      </div>
    </Modal>
  )
}