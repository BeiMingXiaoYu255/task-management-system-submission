/**
 * 加载指示器：用旋转的圆弧表达进行中状态，颜色继承父级文字颜色。
 * 设计上只使用 1 像素级细边与灰阶，不引入彩色。
 */

import styles from './Spinner.module.css'

/** 加载指示器尺寸。 */
export type SpinnerSize = 'small' | 'medium'

/** 加载指示器属性。 */
export interface SpinnerProps {
  /** 尺寸，默认 medium。 */
  size?: SpinnerSize
  /** 无障碍读屏文本，默认“加载中”。 */
  label?: string
  /** 额外样式类名。 */
  className?: string
}

/** 通用加载指示器。 */
export function Spinner({ size = 'medium', label = 'Loading', className }: SpinnerProps) {
  const classNames = [styles.spinner, styles[size]]
  if (className) {
    classNames.push(className)
  }
  return <span className={classNames.join(' ')} role="status" aria-label={label} />
}

export default Spinner
