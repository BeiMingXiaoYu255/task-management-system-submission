/**
 * 进度条：灰阶填充，用于展示完成比例。
 */

import styles from './ProgressBar.module.css'

/** 进度条属性。 */
export interface ProgressBarProps {
  /** 当前值。 */
  value: number
  /** 最大值，默认 100。 */
  max?: number
  /** 无障碍标签，默认“进度”。 */
  label?: string
  /** 额外样式类名。 */
  className?: string
}

/** 进度条组件。 */
export function ProgressBar({ value, max = 100, label = 'Progress', className }: ProgressBarProps) {
  const safeMax = max > 0 ? max : 100
  const clampedValue = Math.min(Math.max(value, 0), safeMax)
  const percentage = Math.round((clampedValue / safeMax) * 100)
  const classNames = [styles.track]
  if (className) {
    classNames.push(className)
  }
  return (
    <div
      className={classNames.join(' ')}
      role="progressbar"
      aria-label={label}
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={safeMax}
    >
      <div className={styles.fill} style={{ width: percentage + '%' }} />
    </div>
  )
}

export default ProgressBar
