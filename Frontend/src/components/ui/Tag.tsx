/**
 * 标签：技能标签、筛选项等场景使用，可关闭。
 */

import type { ReactNode } from 'react'

import styles from './Tag.module.css'

/** 标签属性。 */
export interface TagProps {
  /** 标签文本（也可通过 children 传入）。 */
  label?: string
  /** 标签内容（与 label 二选一）。 */
  children?: ReactNode
  /** 是否显示关闭按钮。 */
  closable?: boolean
  /** 关闭回调。 */
  onClose?: () => void
  /** 额外样式类名。 */
  className?: string
}

/** 标签组件。 */
export function Tag({ label, children, closable = false, onClose, className }: TagProps) {
  const classNames = [styles.tag]
  if (className) {
    classNames.push(className)
  }
  const content = children ?? label
  return (
    <span className={classNames.join(' ')}>
      <span className={styles.text}>{content}</span>
      {closable ? (
        <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Remove tag">
          ×
        </button>
      ) : null}
    </span>
  )
}

export default Tag
