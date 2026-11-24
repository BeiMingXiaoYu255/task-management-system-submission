/**
 * 单选组：使用原生 radio 控件，支持可选的选项描述文本。
 *
 * 类型说明：value/onChange 由泛型 ValueType 约束，保证调用方拿到精确类型；
 * options 的 value 放宽为 string | number，便于调用方直接用普通常量数组
 * （例如任务接受方式/分配方式的枚举选项）而无需 as const。
 */

import { useId } from 'react'

import styles from './RadioGroup.module.css'

/** 单选选项。 */
export interface RadioOption<ValueType extends string | number = string> {
  /** 选项值。 */
  value: ValueType
  /** 选项显示文本。 */
  label: string
  /** 选项补充说明。 */
  description?: string
  /** 是否禁用该选项。 */
  disabled?: boolean
}

/** 单选组属性。 */
export interface RadioGroupProps<ValueType extends string | number = string> {
  /** 当前值。 */
  value: ValueType
  /** 值变化回调。 */
  onChange: (value: ValueType) => void
  /** 选项列表（value 允许使用 string/number 常量，由调用方保证与 value 一致）。 */
  options: RadioOption<string | number>[]
  /** 是否整体禁用。 */
  disabled?: boolean
  /** 额外样式类名。 */
  className?: string
}

/** 单选组组件。 */
export function RadioGroup<ValueType extends string | number = string>({
  value,
  onChange,
  options,
  disabled = false,
  className,
}: RadioGroupProps<ValueType>) {
  const groupName = useId()
  const classNames = [styles.group]
  if (className) {
    classNames.push(className)
  }
  return (
    <div className={classNames.join(' ')} role="radiogroup">
      {options.map((option) => {
        const optionId = groupName + '-' + String(option.value)
        const isDisabled = disabled || option.disabled === true
        return (
          <label key={String(option.value)} className={styles.option} htmlFor={optionId}>
            <input
              id={optionId}
              type="radio"
              className={styles.radio}
              name={groupName}
              value={String(option.value)}
              checked={String(value) === String(option.value)}
              disabled={isDisabled}
              onChange={() => onChange(option.value as ValueType)}
            />
            <span className={styles.textBlock}>
              <span className={styles.label}>{option.label}</span>
              {option.description ? (
                <span className={styles.description}>{option.description}</span>
              ) : null}
            </span>
          </label>
        )
      })}
    </div>
  )
}

export default RadioGroup
