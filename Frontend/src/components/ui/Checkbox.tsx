/**
 * 复选框：使用原生 input 保证键盘与读屏可用，仅用 CSS 变量定制强调色。
 * onChange 透传原生 ChangeEvent，页面通过 event.target.checked 读取状态。
 */

import { useId, type ChangeEvent, type ReactNode } from 'react'

import styles from './Checkbox.module.css'

/** 复选框属性。 */
export interface CheckboxProps {
  /** 是否选中。 */
  checked: boolean
  /** 选中状态变化回调（透传原生事件）。 */
  onChange: (event: ChangeEvent<HTMLInputElement>) => void
  /** 显示在右侧的标签内容。 */
  label?: ReactNode
  /** 是否禁用。 */
  disabled?: boolean
  /** 额外样式类名。 */
  className?: string
}

/** 复选框组件。 */
export function Checkbox({ checked, onChange, label, disabled = false, className }: CheckboxProps) {
  const generatedId = useId()
  const classNames = [styles.wrapper]
  if (disabled) {
    classNames.push(styles.disabled)
  }
  if (className) {
    classNames.push(className)
  }
  return (
    <label className={classNames.join(' ')} htmlFor={generatedId}>
      <input
        id={generatedId}
        type="checkbox"
        className={styles.checkbox}
        checked={checked}
        disabled={disabled}
        onChange={onChange}
      />
      {label ? <span className={styles.label}>{label}</span> : null}
    </label>
  )
}

export default Checkbox
