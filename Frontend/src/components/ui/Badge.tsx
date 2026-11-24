/**
 * 徽标：用于状态/角色等短文本标记，仅使用灰阶深浅与边框区分层级。
 */

import type { ReactNode } from 'react'

import styles from './Badge.module.css'

/** 徽标视觉风格。 */
export type BadgeVariant = 'default' | 'outline' | 'solid'

/** 徽标尺寸。 */
export type BadgeSize = 'small' | 'medium'

/** 徽标属性。 */
export interface BadgeProps {
  /** 视觉风格，默认 default。 */
  variant?: BadgeVariant
  /** 尺寸，默认 medium。 */
  size?: BadgeSize
  /** 徽标内容。 */
  children: ReactNode
  /** 额外样式类名。 */
  className?: string
}

/** 徽标组件。 */
export function Badge({ variant = 'default', size = 'medium', children, className }: BadgeProps) {
  const classNames = [styles.badge, styles[variant], styles[size]]
  if (className) {
    classNames.push(className)
  }
  return <span className={classNames.join(' ')}>{children}</span>
}

export default Badge
