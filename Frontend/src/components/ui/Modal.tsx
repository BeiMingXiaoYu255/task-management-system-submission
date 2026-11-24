/**
 * 模态对话框：通过 Portal 挂载到 body，支持 Esc 关闭、点击遮罩关闭与页内滚动锁定。
 * 弹层使用极淡阴影，保持黑白极简设计语言。
 */

import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import styles from './Modal.module.css'

/** 弹窗宽度档位。 */
export type ModalSize = 'small' | 'medium' | 'large'

/** 模态框属性。 */
export interface ModalProps {
  /** 是否打开。 */
  open: boolean
  /** 标题（可选）。 */
  title?: string
  /** 关闭回调（Esc、遮罩、右上角关闭按钮都会触发）。 */
  onClose: () => void
  /** 底部操作区内容。 */
  footer?: ReactNode
  /** 宽度档位，默认 medium。 */
  size?: ModalSize
  /** 是否允许点击遮罩关闭，默认 true。 */
  closeOnOverlay?: boolean
  /** 弹窗内容。 */
  children: ReactNode
}

/** 模态对话框组件。 */
export function Modal({
  open,
  title,
  onClose,
  footer,
  size = 'medium',
  closeOnOverlay = true,
  children,
}: ModalProps) {
  useEffect(() => {
    if (!open) {
      return
    }
    /** Esc 键关闭弹窗。 */
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  if (!open) {
    return null
  }

  /** 点击遮罩（而非弹窗内部）时关闭。 */
  const handleOverlayMouseDown = (event: React.MouseEvent<HTMLDivElement>): void => {
    if (closeOnOverlay && event.target === event.currentTarget) {
      onClose()
    }
  }

  return createPortal(
    <div className={styles.overlay} role="presentation" onMouseDown={handleOverlayMouseDown}>
      <div
        className={[styles.dialog, styles[size]].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-label={title ?? 'Dialog'}
      >
        {title ? (
          <header className={styles.header}>
            <h2 className={styles.title}>{title}</h2>
            <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close">
              ×
            </button>
          </header>
        ) : null}
        <div className={styles.body}>{children}</div>
        {footer ? <footer className={styles.footer}>{footer}</footer> : null}
      </div>
    </div>,
    document.body,
  )
}

export default Modal
