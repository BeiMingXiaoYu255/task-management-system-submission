/**
 * 页面标题区：标题 + 说明 + 右侧操作区。
 */

import type { ReactNode } from 'react'

import styles from './PageHeader.module.css'

/** 页面标题属性。 */
export interface PageHeaderProps {
  /** 标题。 */
  title: ReactNode
  /** 说明文案。 */
  description?: ReactNode
  /** 右侧操作区。 */
  actions?: ReactNode
}

/** 页面标题区组件。 */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className={styles.pageHeader}>
      <div className={styles.textBlock}>
        <h1 className={styles.title}>{title}</h1>
        {description ? <p className={styles.description}>{description}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  )
}

export default PageHeader
