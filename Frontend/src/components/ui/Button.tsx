/**
 * 通用按钮：支持主要/次要/幽灵/危险四种风格与三种尺寸，内置加载态。
 * 颜色全部来自 tokens.css 的 CSS 变量，保持黑白灰阶设计语言。
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react'

import Spinner from './Spinner'
import styles from './Button.module.css'

/** 按钮视觉风格。 */
export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

/** 按钮尺寸。 */
export type ButtonSize = 'small' | 'medium' | 'large'

/** 按钮属性：在原生按钮属性基础上扩展设计系统字段。 */
export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'> {
  /** 视觉风格，默认 primary。 */
  variant?: ButtonVariant
  /** 尺寸，默认 medium。 */
  size?: ButtonSize
  /** 是否处于加载态（自动禁用交互并显示旋转指示器）。 */
  loading?: boolean
  /** 是否占满整行。 */
  block?: boolean
  /** 原生按钮类型，默认 button，避免意外提交表单。 */
  htmlType?: 'button' | 'submit' | 'reset'
  /** 点击回调，无事件参数（符合前端设计契约）。 */
  onClick?: () => void
  /** 按钮内容。 */
  children: ReactNode
}

/** 通用按钮组件。 */
export function Button({
  variant = 'primary',
  size = 'medium',
  loading = false,
  block = false,
  htmlType = 'button',
  onClick,
  children,
  className,
  disabled = false,
  ...restProps
}: ButtonProps) {
  const classNames = [styles.button, styles[variant], styles[size]]
  if (block) {
    classNames.push(styles.block)
  }
  if (className) {
    classNames.push(className)
  }

  /** 统一处理点击：加载态与禁用态下不触发业务回调。 */
  const handleClick = (): void => {
    if (loading || disabled) {
      return
    }
    if (onClick) {
      onClick()
    }
  }

  return (
    <button
      {...restProps}
      type={htmlType}
      className={classNames.join(' ')}
      disabled={disabled || loading}
      aria-busy={loading ? true : undefined}
      onClick={handleClick}
    >
      {loading ? <Spinner size="small" /> : null}
      <span>{children}</span>
    </button>
  )
}

export default Button
