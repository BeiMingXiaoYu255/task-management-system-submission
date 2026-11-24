/**
 * 空状态：列表无数据时展示标题、说明与可选操作。
 */

import type { ReactNode } from 'react'

import styles from './EmptyState.module.css'

/** 空状态属性。 */
export interface EmptyStateProps {
  /** 主标题。 */
  title: string
  /** 补充说明。 */
  description?: string
  /** 可选操作区（如新建按钮）。 */
  action?: ReactNode
}

/** 空状态组件。 */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      <svg
        className={styles.icon}
        width="32"
        height="32"
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden="true"
      >
        <rect x="5" y="8" width="22" height="17" stroke="currentColor" strokeWidth="1" />
        <path d="M5 13H27" stroke="currentColor" strokeWidth="1" />
        <path d="M12 20H20" stroke="currentColor" strokeWidth="1" />
      </svg>
      <p className={styles.title}>{title}</p>
      {description ? <p className={styles.description}>{description}</p> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  )
}

export default EmptyState
