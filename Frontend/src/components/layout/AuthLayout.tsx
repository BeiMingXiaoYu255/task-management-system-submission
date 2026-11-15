/**
 * 认证页布局：左右分栏的极简版式，左侧品牌说明、右侧表单。
 * ≤900px 时收缩为单列，左侧品牌区仅保留名称。
 */

import type { ReactNode } from 'react'

import styles from './AuthLayout.module.css'

/** 认证页布局属性。 */
export interface AuthLayoutProps {
  /** 表单区标题。 */
  title: string
  /** 表单区补充说明。 */
  subtitle?: string
  /** 表单内容。 */
  children: ReactNode
  /** 表单底部附加内容（如“还没有账号？注册”）。 */
  footer?: ReactNode
}

/** 认证页布局组件。 */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className={styles.container}>
      <aside className={styles.brandPanel}>
        <div className={styles.brandBlock}>
          <span className={styles.brandMark}>T</span>
          <span className={styles.brandName}>Task Management System</span>
        </div>
        <div className={styles.sloganBlock}>
          <p className={styles.slogan}>Minimal. Clear. Efficient.</p>
          <p className={styles.sloganDescription}>
            A grayscale team task collaboration tool: publish tasks, assign and review, track to-dos,
            and manage teams and levels - all in one quiet interface.
          </p>
        </div>
        <p className={styles.brandFooter}>LAN Collaboration Edition</p>
      </aside>
      <main className={styles.formPanel}>
        <div className={styles.formContainer}>
          <header className={styles.formHeader}>
            <h1 className={styles.formTitle}>{title}</h1>
            {subtitle ? <p className={styles.formSubtitle}>{subtitle}</p> : null}
          </header>
          {children}
          {footer ? <div className={styles.formFooter}>{footer}</div> : null}
        </div>
      </main>
    </div>
  )
}

export default AuthLayout
