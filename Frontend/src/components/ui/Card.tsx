/**
 * 卡片容器：细边框、无阴影，标题与操作区可选。
 * padding 同时兼容布尔值与档位字符串，方便不同调用方。
 */

import type { ReactNode } from 'react'

import styles from './Card.module.css'

/** 卡片内边距档位。 */
export type CardPadding = 'none' | 'small' | 'medium' | 'large' | boolean

/** 卡片属性。 */
export interface CardProps {
  /** 卡片标题。 */
  title?: ReactNode
  /** 标题右侧操作区。 */
  actions?: ReactNode
  /** 内边距档位，默认 medium。 */
  padding?: CardPadding
  /** 卡片内容。 */
  children: ReactNode
  /** 额外样式类名。 */
  className?: string
}

/** 把 padding 属性归一化为样式档位。 */
function resolvePaddingModifier(padding: CardPadding | undefined): 'none' | 'small' | 'medium' | 'large' {
  if (padding === undefined || padding === true) {
    return 'medium'
  }
  if (padding === false) {
    return 'none'
  }
  return 'medium' === padding || 'small' === padding || 'large' === padding || 'none' === padding
    ? padding
    : 'medium'
}

/** 卡片容器。 */
export function Card({ title, actions, padding, children, className }: CardProps) {
  const paddingModifier = resolvePaddingModifier(padding)
  const classNames = [styles.card, styles[paddingModifier]]
  if (className) {
    classNames.push(className)
  }
  const hasHeader = Boolean(title) || Boolean(actions)
  return (
    <section className={classNames.join(' ')}>
      {hasHeader ? (
        <header className={styles.header}>
          <div className={styles.title}>{title}</div>
          {actions ? <div className={styles.actions}>{actions}</div> : null}
        </header>
      ) : null}
      <div className={hasHeader ? styles.bodyWithHeader : undefined}>{children}</div>
    </section>
  )
}

export default Card
