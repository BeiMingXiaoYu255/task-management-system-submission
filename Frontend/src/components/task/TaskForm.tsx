/**
 * 任务表单弹窗：发布任务与修改任务的统一入口。
 *
 * 发布模式：基础字段 + AI 自动分配开关 + 所需技能标签 + 接收成员/级别范围选择；
 * 修改模式：仅允许修改标题/描述/优先级/截止时间/接受方式，分配对象只读展示；
 * 校验：标题 2-200 字；未开启自动分配时需选择成员或完整级别范围。
 */

import { useEffect, useState } from 'react'

import { listSkillTags } from '../../api/userApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import { useAsync } from '../../hooks/useAsync'
import { useMemberCandidates } from '../../hooks/useMemberCandidates'
import type { AcceptanceMode, AssignmentMode, TaskPriority } from '../../types/common'
import type { CreateTaskPayload, TaskDetail } from '../../types/task'
import type { MemberCandidateItem, TeamDetail } from '../../types/team'
import type { SkillTagItem } from '../../types/user'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import TaskBasicFields, { type TaskBasicFieldErrors } from './TaskBasicFields'
import TaskTargetSelector from './TaskTargetSelector'
import styles from './TaskForm.module.css'

/** TaskForm 组件属性。 */
export interface TaskFormProps {
  /** 弹窗是否打开。 */
  open: boolean
  /** 任务所属团队详情（提供级别与发布权限信息）。 */
  team: TeamDetail
  /** 修改模式下的原任务；为空表示发布新任务。 */
  initialTask?: TaskDetail | null
  /** 取消回调。 */
  onCancel: () => void
  /** 提交回调；发布成功时返回最新任务详情，便于提示自动分配结果。 */
  onSubmit: (payload: CreateTaskPayload) => Promise<TaskDetail | void>
}

/** 把接口时间格式化为 datetime-local 输入框需要的值（YYYY-MM-DDTHH:mm）。 */
function toDateTimeInputValue(value: string | null | undefined): string {
  if (!value) {
    return ''
  }
  return value.length >= 16 ? value.slice(0, 16) : value
}

/** 把 datetime-local 输入值转换为接口使用的本地 ISO 时间字符串。 */
function toApiDateTimeValue(value: string): string | null {
  const trimmedValue = value.trim()
  if (trimmedValue === '') {
    return null
  }
  return trimmedValue.length === 16 ? trimmedValue + ':00' : trimmedValue
}

/** 把可空级别转换为级别下拉框使用的字符串值。 */
function toLevelInputValue(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value)
}

/** 所需技能标签数量上限（与后端请求校验一致）。 */
const MAX_REQUIRED_SKILL_COUNT = 30

/** 任务表单弹窗。 */
export default function TaskForm({
  open,
  team,
  initialTask = null,
  onCancel,
  onSubmit,
}: TaskFormProps) {
  const { showToast } = useToast()
  const isEditMode = initialTask !== null
  const [title, setTitle] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [priority, setPriority] = useState<string>('medium')
  const [dueAt, setDueAt] = useState<string>('')
  const [acceptanceMode, setAcceptanceMode] = useState<AcceptanceMode>('mandatory')
  const [assignmentMode, setAssignmentMode] = useState<AssignmentMode>('specific')
  const [autoAssign, setAutoAssign] = useState<boolean>(false)
  const [requiredSkillNames, setRequiredSkillNames] = useState<string[]>([])
  const [targetUserIds, setTargetUserIds] = useState<number[]>([])
  const [targetLevelMin, setTargetLevelMin] = useState<string>('')
  const [targetLevelMax, setTargetLevelMax] = useState<string>('')
  const [basicErrors, setBasicErrors] = useState<TaskBasicFieldErrors>({})
  const [targetError, setTargetError] = useState<string | undefined>(undefined)
  const [submitting, setSubmitting] = useState<boolean>(false)

  /** 技能标签字典：仅发布模式打开时加载，失败可在表单内重试。 */
  const skillTagsState = useAsync<SkillTagItem[]>(
    () => (open && !isEditMode ? listSkillTags() : Promise.resolve([])),
    [open, isEditMode],
  )

  /** 指定成员模式需要候选成员；自动分配模式与修改模式不请求。 */
  const candidatesState = useMemberCandidates(
    team.id,
    open && !isEditMode && !autoAssign && assignmentMode === 'specific',
  )

  /** 候选接口仅管理员/子管理员可调用；普通发布者回退为团队详情中的成员列表。 */
  const fallbackCandidates: MemberCandidateItem[] = team.members.map((member) => ({
    userId: member.userId, username: member.username, nickname: member.nickname, avatar: member.avatar,
    role: member.role, levelId: member.levelId, levelName: member.levelName, levelOrder: member.levelOrder,
    skills: member.skills,
  }))
  const availableCandidates =
    candidatesState.error !== null || candidatesState.data === null ? fallbackCandidates : candidatesState.data

  /** 打开弹窗时初始化/重置表单。 */
  useEffect(() => {
    if (!open) {
      return
    }
    setTitle(initialTask?.title ?? '')
    setDescription(initialTask?.description ?? '')
    setPriority(initialTask?.priority ?? 'medium')
    setDueAt(toDateTimeInputValue(initialTask?.dueAt))
    setAcceptanceMode(initialTask?.acceptanceMode ?? 'mandatory')
    setAssignmentMode(initialTask?.assignmentMode ?? 'specific')
    setAutoAssign(initialTask?.autoAssigned ?? false)
    setRequiredSkillNames(initialTask?.requiredSkillNames ?? [])
    setTargetUserIds(initialTask?.assignments.map((assignment) => assignment.userId) ?? [])
    setTargetLevelMin(toLevelInputValue(initialTask?.targetLevelMin))
    setTargetLevelMax(toLevelInputValue(initialTask?.targetLevelMax))
    setBasicErrors({})
    setTargetError(undefined)
  }, [open, initialTask])

  /** 校验表单并构造接口请求体；校验失败返回 null。 */
  const validateAndBuildPayload = (): CreateTaskPayload | null => {
    const nextBasicErrors: TaskBasicFieldErrors = {}
    const trimmedTitle = title.trim()
    if (trimmedTitle.length < 2 || trimmedTitle.length > 200) {
      nextBasicErrors.title = 'Task title must be 2-200 characters.'
    }
    let nextTargetError: string | undefined
    if (!isEditMode && !autoAssign) {
      if (assignmentMode === 'specific') {
        if (targetUserIds.length === 0) {
          nextTargetError = 'Select at least one assignee.'
        } else if (targetUserIds.length > 100) {
          nextTargetError = 'You can select at most 100 assignees.'
        }
      } else if (targetLevelMin === '' || targetLevelMax === '') {
        nextTargetError = 'Select a complete level range.'
      } else if (Number(targetLevelMin) > Number(targetLevelMax)) {
        nextTargetError = 'The minimum level cannot be higher than the maximum level.'
      }
    }
    setBasicErrors(nextBasicErrors)
    setTargetError(nextTargetError)
    if (Object.keys(nextBasicErrors).length > 0 || nextTargetError !== undefined) {
      return null
    }
    const payload: CreateTaskPayload = {
      title: trimmedTitle,
      description: description.trim() === '' ? null : description.trim(),
      priority: priority as TaskPriority,
      dueAt: toApiDateTimeValue(dueAt),
      assignmentMode,
      acceptanceMode,
    }
    if (!isEditMode && autoAssign) {
      payload.autoAssign = true
      if (requiredSkillNames.length > 0) {
        payload.requiredSkillNames = requiredSkillNames
      }
    } else if (assignmentMode === 'specific') {
      payload.targetUserIds = targetUserIds
    } else if (!isEditMode) {
      payload.targetLevelMin = Number(targetLevelMin)
      payload.targetLevelMax = Number(targetLevelMax)
    }
    return payload
  }

  /** 提交表单：先校验，再调用父级回调；自动分配无匹配时提示手动指派。 */
  const handleSubmit = async (): Promise<void> => {
    const payload = validateAndBuildPayload()
    if (payload === null) {
      return
    }
    setSubmitting(true)
    try {
      const createdTask = await onSubmit(payload)
      if (payload.autoAssign === true) {
        if (createdTask && createdTask.assignments.length === 0) {
          showToast('Task published, but no suitable assignee matched. You can assign one from the task details page.', 'info')
        } else if (!createdTask) {
          showToast('Task published. If AI does not match an assignee, you can assign one from the task details page.', 'info')
        }
      }
    } catch (caughtError: unknown) {
      showToast(getErrorMessage(caughtError, 'Failed to submit task. Please try again.'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  /** 分配方式切换：清空目标相关错误。 */
  const handleAssignmentModeChange = (nextMode: AssignmentMode): void => {
    setAssignmentMode(nextMode)
    setTargetError(undefined)
  }

  /** 切换单个所需技能标签（最多 30 个）。 */
  const handleToggleSkill = (skillName: string): void => {
    if (!requiredSkillNames.includes(skillName) && requiredSkillNames.length >= MAX_REQUIRED_SKILL_COUNT) {
      showToast('You can select at most ' + String(MAX_REQUIRED_SKILL_COUNT) + ' skill tags.', 'info')
      return
    }
    setRequiredSkillNames((previousNames) =>
      previousNames.includes(skillName) ? previousNames.filter((name) => name !== skillName) : [...previousNames, skillName])
  }

  /** 底部操作区。 */
  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onCancel} disabled={submitting}>
        Cancel
      </Button>
      <Button onClick={() => void handleSubmit()} loading={submitting}>
        {isEditMode ? 'Save Changes' : 'Publish Task'}
      </Button>
    </div>
  )

  return (
    <Modal
      open={open}
      title={isEditMode ? 'Edit Task' : 'Publish Task'}
      size="large"
      footer={footer}
      onClose={() => {
        if (!submitting) {
          onCancel()
        }
      }}
    >
      <div className={styles.formBody}>
        <p className={styles.teamHint}>
          {isEditMode ? 'Team: ' : 'Publish to team: '}
          {team.name}
        </p>
        <TaskBasicFields
          title={title} description={description} priority={priority} dueAt={dueAt}
          acceptanceMode={acceptanceMode} errors={basicErrors} disabled={submitting}
          showAutoAssign={!isEditMode} autoAssign={autoAssign}
          requiredSkillNames={requiredSkillNames}
          availableSkillTags={skillTagsState.data ?? []}
          skillTagsLoading={skillTagsState.loading} skillTagsError={skillTagsState.error}
          onTitleChange={setTitle} onDescriptionChange={setDescription}
          onPriorityChange={setPriority} onDueAtChange={setDueAt}
          onAcceptanceModeChange={setAcceptanceMode}
          onAutoAssignChange={(nextAutoAssign) => {
            setAutoAssign(nextAutoAssign)
            setTargetError(undefined)
          }}
          onToggleSkill={handleToggleSkill} onReloadSkillTags={skillTagsState.reload}
        />
        {isEditMode && initialTask ? (
          <div className={styles.targetSummary}>
            <span className={styles.targetSummaryLabel}>Assignees (cannot be changed when editing)</span>
            <span>
              {initialTask.autoAssigned
                ? 'AI Auto-assignment' +
                  (initialTask.assignments.length > 0
                    ? ' · ' + initialTask.assignments.map((assignment) => assignment.nickname).join(', ')
                    : ' (No assignees yet. You can assign them from the task details page.)')
                : initialTask.assignmentMode === 'specific'
                  ? initialTask.assignments.map((assignment) => assignment.nickname).join(', ')
                  : 'Level Range ' + String(initialTask.targetLevelMin ?? '-') +
                    ' ~ ' + String(initialTask.targetLevelMax ?? '-')}
            </span>
          </div>
        ) : (
          <TaskTargetSelector
            teamId={team.id} assignmentMode={assignmentMode} autoAssign={autoAssign}
            requiredSkillNames={requiredSkillNames}
            targetUserIds={targetUserIds} targetLevelMin={targetLevelMin} targetLevelMax={targetLevelMax}
            levels={team.levels} candidates={availableCandidates}
            candidatesLoading={candidatesState.loading && candidatesState.error === null}
            candidatesError={availableCandidates.length === 0 ? candidatesState.error : null}
            currentUserRole={team.currentUserRole} currentUserLevelOrder={team.currentUserLevelOrder}
            taskTitle={title} taskDescription={description} taskPriority={priority}
            error={targetError} onModeChange={handleAssignmentModeChange}
            onTargetUserIdsChange={setTargetUserIds}
            onLevelRangeChange={(nextLevelMin, nextLevelMax) => {
              setTargetLevelMin(nextLevelMin)
              setTargetLevelMax(nextLevelMax)
            }}
          />
        )}
      </div>
    </Modal>
  )
}
