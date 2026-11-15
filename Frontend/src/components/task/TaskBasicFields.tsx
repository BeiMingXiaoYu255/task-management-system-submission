/**
 * 任务基础字段组：标题、描述、优先级、截止时间、接受方式，
 * 以及发布模式下的「AI 自动分配」开关与「所需技能标签」多选。
 *
 * 纯展示组件：所有值由父级（TaskForm）持有，仅回调变化与校验错误，
 * 便于发布/修改两种模式复用同一套字段布局。
 */

import type { AcceptanceMode } from '../../types/common'
import type { SkillTagItem } from '../../types/user'
import Button from '../ui/Button'
import Checkbox from '../ui/Checkbox'
import Input from '../ui/Input'
import RadioGroup from '../ui/RadioGroup'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import styles from './TaskBasicFields.module.css'

/** 任务基础字段错误信息。 */
export interface TaskBasicFieldErrors {
  /** 标题错误。 */
  title?: string
  /** 截止时间错误。 */
  dueAt?: string
}

/** TaskBasicFields 组件属性。 */
export interface TaskBasicFieldsProps {
  title: string
  description: string
  priority: string
  dueAt: string
  acceptanceMode: AcceptanceMode
  errors: TaskBasicFieldErrors
  disabled?: boolean
  /** 是否展示 AI 自动分配相关字段（仅发布模式）。 */
  showAutoAssign?: boolean
  /** 是否开启 AI 自动分配。 */
  autoAssign?: boolean
  /** 已选所需技能标签名称。 */
  requiredSkillNames?: string[]
  /** 全部可选技能标签（来源 GET /skill-tags）。 */
  availableSkillTags?: SkillTagItem[]
  /** 技能标签是否加载中。 */
  skillTagsLoading?: boolean
  /** 技能标签加载失败提示。 */
  skillTagsError?: string | null
  onTitleChange: (title: string) => void
  onDescriptionChange: (description: string) => void
  onPriorityChange: (priority: string) => void
  onDueAtChange: (dueAt: string) => void
  onAcceptanceModeChange: (acceptanceMode: AcceptanceMode) => void
  /** 自动分配开关变化。 */
  onAutoAssignChange?: (autoAssign: boolean) => void
  /** 切换单个技能标签。 */
  onToggleSkill?: (skillName: string) => void
  /** 重新加载技能标签字典。 */
  onReloadSkillTags?: () => void
}

/** 优先级下拉选项。 */
const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

/** 接受方式选项。 */
const ACCEPTANCE_MODE_OPTIONS = [
  {
    value: 'mandatory',
    label: 'Mandatory',
    description: 'The task starts In Progress immediately; assignees cannot reject it.',
  },
  {
    value: 'optional',
    label: 'Optional',
    description: 'Assignees can accept or reject; rejected assignments are removed.',
  },
]

/** 任务基础字段组。 */
export default function TaskBasicFields({
  title,
  description,
  priority,
  dueAt,
  acceptanceMode,
  errors,
  disabled = false,
  showAutoAssign = false,
  autoAssign = false,
  requiredSkillNames = [],
  availableSkillTags = [],
  skillTagsLoading = false,
  skillTagsError = null,
  onTitleChange,
  onDescriptionChange,
  onPriorityChange,
  onDueAtChange,
  onAcceptanceModeChange,
  onAutoAssignChange,
  onToggleSkill,
  onReloadSkillTags,
}: TaskBasicFieldsProps) {
  return (
    <div className={styles.fieldGroup}>
      <Input
        label="Task Title *"
        value={title}
        onChange={(event) => onTitleChange(event.target.value)}
        placeholder="2-200 characters; briefly describe the task goal"
        error={errors.title}
        disabled={disabled}
        maxLength={200}
      />
      <Textarea
        label="Task Description"
        value={description}
        onChange={(event) => onDescriptionChange(event.target.value)}
        placeholder="Add context, delivery criteria, and notes"
        rows={4}
        disabled={disabled}
      />
      <div className={styles.twoColumns}>
        <Select
          label="Priority"
          value={priority}
          onChange={(nextValue) => onPriorityChange(String(nextValue))}
          options={PRIORITY_OPTIONS}
          disabled={disabled}
        />
        <Input
          label="Due Date"
          type="datetime-local"
          value={dueAt}
          onChange={(event) => onDueAtChange(event.target.value)}
          error={errors.dueAt}
          disabled={disabled}
        />
      </div>
      <div className={styles.section}>
        <span className={styles.sectionLabel}>Acceptance Mode</span>
        <RadioGroup<AcceptanceMode>
          value={acceptanceMode}
          onChange={onAcceptanceModeChange}
          options={ACCEPTANCE_MODE_OPTIONS}
          disabled={disabled}
        />
      </div>

      {showAutoAssign ? (
        <>
          <div className={styles.section}>
            <span className={styles.sectionLabel}>AI Auto-assignment</span>
            <Checkbox
              checked={autoAssign}
              disabled={disabled}
              onChange={(event) => onAutoAssignChange?.(event.target.checked)}
              label={
                <span className={styles.checkboxLabel}>
                  Enable AI Auto-assignment
                  <span className={styles.checkboxHint}>
                    The dispatcher selects assignees from the task content and required skills at publish time.
                  </span>
                </span>
              }
            />
            <p className={styles.hint}>
              {autoAssign
                ? 'Auto-assignment is on: no need to select members manually. If nothing matches, the task stays Pending Assignment and the publisher can assign it from the task details page.'
                : 'When off, select members or a level range below.'}
            </p>
          </div>

          <div className={styles.section}>
            <span className={styles.sectionLabel}>Required Skill Tags (optional, up to 30)</span>
            <p className={styles.hint}>
              Used for AI recommendations and auto-assignment. If empty, they are inferred from the title and description.
            </p>
            {skillTagsLoading ? <p className={styles.hint}>Loading skill tags...</p> : null}
            {skillTagsError !== null ? (
              <div className={styles.skillErrorRow}>
                <span className={styles.errorText}>{skillTagsError}</span>
                <Button
                  variant="ghost"
                  size="small"
                  onClick={() => onReloadSkillTags?.()}
                >
                  Retry
                </Button>
              </div>
            ) : null}
            {!skillTagsLoading && skillTagsError === null && availableSkillTags.length === 0 ? (
              <p className={styles.hint}>No skill tags yet. Add them on your Profile page.</p>
            ) : null}
            <div className={styles.skillTags}>
              {availableSkillTags.map((skillTag) => {
                const selected = requiredSkillNames.includes(skillTag.name)
                return (
                  <button
                    key={skillTag.id}
                    type="button"
                    className={
                      selected
                        ? styles.skillTag + ' ' + styles.skillTagSelected
                        : styles.skillTag
                    }
                    aria-pressed={selected}
                    disabled={disabled}
                    onClick={() => onToggleSkill?.(skillTag.name)}
                  >
                    {skillTag.name}
                  </button>
                )
              })}
            </div>
            {requiredSkillNames.length > 0 ? (
              <p className={styles.hint}>
                Selected {requiredSkillNames.length} skills: {requiredSkillNames.join(', ')}
              </p>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  )
}
