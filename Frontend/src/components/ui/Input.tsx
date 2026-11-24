/**
 * 单行文本输入框：包含标签、提示、错误文案与聚焦态。
 * onChange 直接透传原生 ChangeEvent，便于页面按 React 惯例取值。
 */

import { useId, type ChangeEvent, type KeyboardEvent } from 'react'

import styles from './Input.module.css'

/** 输入框属性。 */
export interface InputProps {
  /** 标签文本。 */
  label?: string
  /** 错误文案（存在时优先于 hint 显示，且边框变危险色）。 */
  error?: string
  /** 辅助提示文案。 */
  hint?: string
  /** 当前值。 */
  value: string
  /** 值变化回调（透传原生事件）。 */
  onChange: (event: ChangeEvent<HTMLInputElement>) => void
  /** 占位文本。 */
  placeholder?: string
  /** 原生输入类型，默认 text。 */
  type?: string
  /** 是否禁用。 */
  disabled?: boolean
  /** 是否自动聚焦。 */
  autoFocus?: boolean
  /** 键盘事件回调（如回车提交）。 */
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void
  /** 表单字段名。 */
  name?: string
  /** 自定义 id（不传时自动生成）。 */
  id?: string
  /** 最大输入长度。 */
  maxLength?: number
  /** 浏览器自动填充提示。 */
  autoComplete?: string
  /** 是否必填（仅用于原生语义）。 */
  required?: boolean
  /** 额外样式类名。 */
  className?: string
}

/** 单行文本输入框。 */
export function Input({
  label,
  error,
  hint,
  value,
  onChange,
  placeholder,
  type = 'text',
  disabled = false,
  autoFocus = false,
  onKeyDown,
  name,
  id,
  maxLength,
  autoComplete,
  required = false,
  className,
}: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const classNames = [styles.input]
  if (error) {
    classNames.push(styles.inputError)
  }
  if (className) {
    classNames.push(className)
  }
  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        name={name}
        className={classNames.join(' ')}
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        autoComplete={autoComplete}
        maxLength={maxLength}
        required={required}
        aria-invalid={error ? true : undefined}
        onChange={onChange}
        onKeyDown={onKeyDown}
      />
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

export default Input
