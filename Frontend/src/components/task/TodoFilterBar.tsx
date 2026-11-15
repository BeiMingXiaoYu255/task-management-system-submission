/**
 * 待办筛选栏：状态、优先级、团队、关键词、排序与“包含已归档”开关。
 *
 * 与任务筛选栏的区别：待办状态使用分配状态枚举（待接受/进行中/待审核），
 * 且排序支持按优先级/截止时间/创建时间，关键词输入同样做 300ms 防抖。
 */

import { useEffect, useState } from 'react'

import Button from '../ui/Button'
import Checkbox from '../ui/Checkbox'
import Input from '../ui/Input'
import Select from '../ui/Select'
import { ASSIGNMENT_STATUS_LABELS, PRIORITY_LABELS } from '../../utils/displayUtils'
import styles from './TodoFilterBar.module.css'

/** 待办筛选条件。 */
export interface TodoFilterValues {
  /** 待办状态；空字符串表示全部未归档。 */
  status: string
  /** 优先级；空字符串表示全部。 */
  priority: string
  /** 团队筛选；空字符串表示全部团队。 */
  teamId: string
  /** 关键词。 */
  keyword: string
  /** 排序字段。 */
  sortBy: 'priority' | 'dueAt' | 'createdAt'
  /** 排序方向。 */
  sortOrder: 'asc' | 'desc'
  /** 是否包含已归档待办。 */
  includeArchived: boolean
}

/** 默认待办筛选条件：全部未归档，按创建时间倒序。 */
export const DEFAULT_TODO_FILTERS: TodoFilterValues = {
  status: '',
  priority: '',
  teamId: '',
  keyword: '',
  sortBy: 'createdAt',
  sortOrder: 'desc',
  includeArchived: false,
}

/** 关键词防抖延迟（毫秒）。 */
const KEYWORD_DEBOUNCE_MILLISECONDS = 300

/** TodoFilterBar 组件属性。 */
export interface TodoFilterBarProps {
  /** 当前筛选条件。 */
  values: TodoFilterValues
  /** 筛选条件变化回调。 */
  onChange: (values: TodoFilterValues) => void
  /** 团队下拉选项。 */
  teamOptions: { value: number; label: string }[]
  /** 刷新回调。 */
  onRefresh?: () => void
  /** 刷新按钮加载态。 */
  refreshing?: boolean
}

/** 待办筛选栏。 */
export default function TodoFilterBar({
  values,
  onChange,
  teamOptions,
  onRefresh,
  refreshing = false,
}: TodoFilterBarProps) {
  const [keywordDraft, setKeywordDraft] = useState<string>(values.keyword)

  /** 外部关键词变化时同步输入框。 */
  useEffect(() => {
    setKeywordDraft(values.keyword)
  }, [values.keyword])

  /** 关键词防抖提交。 */
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
  const updateFilter = (patch: Partial<TodoFilterValues>): void => {
    onChange({ ...values, ...patch })
  }

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    ...Object.entries(ASSIGNMENT_STATUS_LABELS)
      .filter(([statusValue]) => statusValue !== 'archived')
      .map(([statusValue, statusLabel]) => ({ value: statusValue, label: statusLabel })),
  ]
  const priorityOptions = [
    { value: '', label: 'All Priorities' },
    ...Object.entries(PRIORITY_LABELS).map(([priorityValue, priorityLabel]) => ({
      value: priorityValue,
      label: priorityLabel,
    })),
  ]
  const sortOptions = [
    { value: 'priority', label: 'Priority' },
    { value: 'dueAt', label: 'Due Date' },
    { value: 'createdAt', label: 'Created' },
  ]

  return (
    <div className={styles.filterBar} role="search">
      <div className={styles.filterRow}>
        <Input
          label="Keyword"
          value={keywordDraft}
          onChange={(event) => setKeywordDraft(event.target.value)}
          placeholder="Search to-do title or description"
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
        <Select
          label="Team"
          value={values.teamId}
          onChange={(nextValue) => updateFilter({ teamId: String(nextValue) })}
          options={[
            { value: '', label: 'All Teams' },
            ...teamOptions.map((teamOption) => ({ value: teamOption.value, label: teamOption.label })),
          ]}
        />
        <Select
          label="Sort"
          value={values.sortBy}
          onChange={(nextValue) =>
            updateFilter({ sortBy: String(nextValue) as TodoFilterValues['sortBy'] })
          }
          options={sortOptions}
        />
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
        {onRefresh ? (
          <div className={styles.refreshBox}>
            <Button variant="ghost" size="small" onClick={onRefresh} loading={refreshing}>
              Refresh
            </Button>
          </div>
        ) : null}
      </div>
      <div className={styles.optionRow}>
        <Checkbox
          checked={values.includeArchived}
          onChange={(event) => updateFilter({ includeArchived: event.target.checked })}
          label="Include archived to-dos"
        />
      </div>
    </div>
  )
}
