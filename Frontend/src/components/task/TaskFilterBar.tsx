/**
 * 任务筛选栏：状态、优先级、关键词、排序（可选团队过滤）。
 *
 * 实现要点：
 * 1. 关键词输入内部维护草稿态并做 300ms 防抖，避免每次按键都触发请求；
 * 2. 外部 values.keyword 变化时同步草稿，保证重置/回填场景正确；
 * 3. 排序由“排序字段 + 升降序切换按钮”组合，点击按钮切换 asc/desc。
 */

import { useEffect, useState, type ReactNode } from 'react'

import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import { TASK_STATUS_LABELS, getPriorityLabel, getTaskStatusLabel } from '../../utils/displayUtils'
import type { TaskPriority, TaskStatus } from '../../types/common'
import styles from './TaskFilterBar.module.css'

/** 任务筛选条件（页面状态）。 */
export interface TaskFilterValues {
  /** 任务状态；空字符串表示全部。 */
  status: string
  /** 优先级；空字符串表示全部。 */
  priority: string
  /** 关键词。 */
  keyword: string
  /** 排序字段。 */
  sortBy: 'createdAt' | 'dueAt' | 'priority'
  /** 排序方向。 */
  sortOrder: 'asc' | 'desc'
  /** 团队筛选（仅任务中心使用）；空字符串表示全部团队。 */
  teamId: string
}

/** 默认筛选条件：按创建时间倒序。 */
export const DEFAULT_TASK_FILTERS: TaskFilterValues = {
  status: '',
  priority: '',
  keyword: '',
  sortBy: 'createdAt',
  sortOrder: 'desc',
  teamId: '',
}

/** 关键词防抖延迟（毫秒）。 */
const KEYWORD_DEBOUNCE_MILLISECONDS = 300

/** TaskFilterBar 组件属性。 */
export interface TaskFilterBarProps {
  /** 当前筛选条件。 */
  values: TaskFilterValues
  /** 筛选条件变化回调。 */
  onChange: (values: TaskFilterValues) => void
  /** 是否展示排序控件。 */
  showSort?: boolean
  /** 团队下拉选项（传入后展示团队筛选）。 */
  teamOptions?: { value: number; label: string }[]
  /** 右侧额外操作区。 */
  extraActions?: ReactNode
  /** 刷新回调；传入后展示刷新按钮。 */
  onRefresh?: () => void
  /** 刷新按钮是否处于加载态。 */
  refreshing?: boolean
}

/** 生成任务状态下拉选项。 */
function buildStatusOptions(): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [{ value: '', label: 'All Statuses' }]
  Object.entries(TASK_STATUS_LABELS).forEach(([statusValue, statusLabel]) => {
    options.push({ value: statusValue, label: statusLabel })
  })
  return options
}

/** 生成优先级下拉选项。 */
function buildPriorityOptions(): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [{ value: '', label: 'All Priorities' }]
  const priorityValues: TaskPriority[] = ['urgent', 'high', 'medium', 'low']
  priorityValues.forEach((priorityValue) => {
    options.push({ value: priorityValue, label: getPriorityLabel(priorityValue) })
  })
  return options
}

/** 生成排序字段下拉选项。 */
function buildSortOptions(): { value: string; label: string }[] {
  return [
    { value: 'createdAt', label: 'Created' },
    { value: 'dueAt', label: 'Due Date' },
    { value: 'priority', label: 'Priority' },
  ]
}

/** 任务筛选栏组件。 */
export default function TaskFilterBar({
  values,
  onChange,
  showSort = true,
  teamOptions,
  extraActions,
  onRefresh,
  refreshing = false,
}: TaskFilterBarProps) {
  const [keywordDraft, setKeywordDraft] = useState<string>(values.keyword)

  /** 外部关键词变化（重置/回填）时同步输入框。 */
  useEffect(() => {
    setKeywordDraft(values.keyword)
  }, [values.keyword])

  /** 关键词防抖：草稿变化后延迟提交给父组件。 */
  useEffect(() => {
    if (keywordDraft === values.keyword) {
      return undefined
    }
    const timerIdentifier = window.setTimeout(() => {
      onChange({ ...values, keyword: keywordDraft })
    }, KEYWORD_DEBOUNCE_MILLISECONDS)
    return () => {
      window.clearTimeout(timerIdentifier)
    }
    // 仅在草稿变化时重新计时
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keywordDraft])

  /** 更新单个筛选字段。 */
  const updateFilter = (patch: Partial<TaskFilterValues>): void => {
    onChange({ ...values, ...patch })
  }

  const statusOptions = buildStatusOptions()
  const priorityOptions = buildPriorityOptions()
  const sortOptions = buildSortOptions()
  const teamSelectOptions =
    teamOptions?.map((teamOption) => ({ value: teamOption.value, label: teamOption.label })) ?? []

  return (
    <div className={styles.filterBar} role="search">
      <div className={styles.filterRow}>
        <Input
          label="Keyword"
          value={keywordDraft}
          onChange={(event) => setKeywordDraft(event.target.value)}
          placeholder="Search task title or description"
        />
        <Select
          label="Status"
          value={values.status}
          onChange={(nextValue) => updateFilter({ status: String(nextValue) })}
          options={statusOptions}
        />
        <Select
          label="Priority"
          value={values.priority}
          onChange={(nextValue) => updateFilter({ priority: String(nextValue) })}
          options={priorityOptions}
        />
        {teamOptions && teamOptions.length > 0 ? (
          <Select
            label="Team"
            value={values.teamId}
            onChange={(nextValue) => updateFilter({ teamId: String(nextValue) })}
            options={[{ value: '', label: 'All Teams' }, ...teamSelectOptions]}
          />
        ) : null}
        {showSort ? (
          <Select
            label="Sort"
            value={values.sortBy}
            onChange={(nextValue) =>
              updateFilter({ sortBy: String(nextValue) as TaskFilterValues['sortBy'] })
            }
            options={sortOptions}
          />
        ) : null}
        {showSort ? (
          <div className={styles.sortOrderBox}>
            <span className={styles.sortOrderLabel}>Order</span>
            <Button
              variant="secondary"
              size="small"
              onClick={() =>
                updateFilter({ sortOrder: values.sortOrder === 'asc' ? 'desc' : 'asc' })
              }
              title="Toggle ascending/descending"
            >
              {values.sortOrder === 'asc' ? 'Ascending ↑' : 'Descending ↓'}
            </Button>
          </div>
        ) : null}
        {onRefresh ? (
          <div className={styles.refreshBox}>
            <Button variant="ghost" size="small" onClick={onRefresh} loading={refreshing}>
              Refresh
            </Button>
          </div>
        ) : null}
      </div>
      {extraActions ? <div className={styles.extraActions}>{extraActions}</div> : null}
    </div>
  )
}

/** 把筛选条件转换为后端查询参数（去掉空值）。 */
export function toTaskQuery(values: TaskFilterValues): {
  status?: string
  priority?: string
  keyword?: string
  teamId?: number
  sortBy: 'createdAt' | 'dueAt' | 'priority'
  sortOrder: 'asc' | 'desc'
} {
  return {
    status: values.status || undefined,
    priority: values.priority || undefined,
    keyword: values.keyword.trim() || undefined,
    teamId: values.teamId ? Number(values.teamId) : undefined,
    sortBy: values.sortBy,
    sortOrder: values.sortOrder,
  }
}

/** 生成状态下拉的中文标签（供页面在筛选摘要中复用）。 */
export function describeTaskStatus(status: string): string {
  return status ? getTaskStatusLabel(status as TaskStatus) : 'All Statuses'
}
