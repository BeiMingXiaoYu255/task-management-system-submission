/**
 * 多行文本输入框：与 Input 保持一致的标签/错误/提示结构。
 * onChange 直接透传原生 ChangeEvent。
 */

import { useId, type ChangeEvent } from 'react'

import styles from './Textarea.module.css'

/** 多行输入框属性。 */
export interface TextareaProps {
  /** 标签文本。 */
  label?: string
  /** 错误文案。 */
  error?: string
  /** 辅助提示。 */
  hint?: string
  /** 当前值。 */
  value: string
  /** 值变化回调（透传原生事件）。 */
  onChange: (event: ChangeEvent<HTMLTextAreaElement>) => void
  /** 显示行数，默认 4。 */
  rows?: number
  /** 占位文本。 */
  placeholder?: string
  /** 最大长度。 */
  maxLength?: number
  /** 是否禁用。 */
  disabled?: boolean
  /** 表单字段名。 */
  name?: string
  /** 自定义 id。 */
  id?: string
  /** 额外样式类名。 */
  className?: string
}

/** 多行文本输入框。 */
export function Textarea({
  label,
  error,
  hint,
  value,
  onChange,
  rows = 4,
  placeholder,
  maxLength,
  disabled = false,
  name,
  id,
  className,
}: TextareaProps) {
  const generatedId = useId()
  const textareaId = id ?? generatedId
  const classNames = [styles.textarea]
  if (error) {
    classNames.push(styles.textareaError)
  }
  if (className) {
    classNames.push(className)
  }
  return (
    <div className={styles.field}>
      {label ? (
        <label className={styles.label} htmlFor={textareaId}>
          {label}
        </label>
      ) : null}
      <textarea
        id={textareaId}
        name={name}
        className={classNames.join(' ')}
        value={value}
        rows={rows}
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        onChange={onChange}
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

export default Textarea
