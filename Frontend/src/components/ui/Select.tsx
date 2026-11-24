/**
 * 下拉选择框：原生 select 保证可访问性与移动端体验，外观用 CSS 变量定制。
 * onChange 返回选项的原始值（保留 number/string 类型）。
 */

import { useId } from 'react'

import styles from './Select.module.css'

/** 下拉选项。 */
export interface SelectOption {
  /** 选项值，可为字符串或数字。 */
  value: string | number
  /** 选项显示文本。 */
  label: string
}

/** 下拉选择框属性。 */
export interface SelectProps {
  /** 标签文本。 */
  label?: string
  /** 错误文案。 */
  error?: string
  /** 辅助提示。 */
  hint?: string
  /** 当前选中值。 */
  value: string | number
  /** 选中变化回调，返回原始类型的值。 */
  onChange: (value: string | number) => void
  /** 选项列表。 */
  options: SelectOption[]
  /** 占位文本（作为空值选项展示）。 */
  placeholder?: string
  /** 是否禁用。 */
  disabled?: boolean
  /** 表单字段名。 */
  name?: string
  /** 自定义 id。 */
  id?: string
  /** 额外样式类名。 */
  className?: string
}

/** 下拉选择框。 */
export function Select({
  label,
  error,
  hint,
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  name,
  id,
  className,
}: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const classNames = [styles.select]
  if (error) {
    classNames.push(styles.selectError)
  }
  if (className) {
    classNames.push(className)
  }

  /** 把原生字符串值映射回选项的原始类型后回调。 */
  const handleChange = (rawValue: string): void => {
    const matchedOption = options.find((option) => String(option.value) === rawValue)
    if (matchedOption) {
      onChange(matchedOption.value)
    }
  }

  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.label} htmlFor={selectId}>
          {label}
        </label>
      ) : null}
      <div className={styles.selectWrapper}>
        <select
          id={selectId}
          name={name}
          className={classNames.join(' ')}
          value={String(value)}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          onChange={(event) => handleChange(event.target.value)}
        >
          {placeholder ? (
            <option value="" disabled>
              {placeholder}
            </option>
          ) : null}
          {options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.label}
            </option>
          ))}
        </select>
        <svg
          className={styles.chevron}
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          aria-hidden="true"
        >
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.2" />
        </svg>
      </div>
      {error ? (
        <span className={styles.error} role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className={styles.hint}>{hint}</span>
      ) : null}
    </div>
  )
}

export default Select
