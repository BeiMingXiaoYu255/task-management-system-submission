/**
 * 二次确认对话框：基于 Modal 的轻量封装，危险操作使用低饱和危险色按钮。
 */

import type { ReactNode } from 'react'

import Button from './Button'
import Modal from './Modal'
import styles from './ConfirmDialog.module.css'

/** 二次确认对话框属性。 */
export interface ConfirmDialogProps {
  /** 是否打开。 */
  open: boolean
  /** 标题。 */
  title: string
  /** 说明文案（可传 ReactNode 以插入高亮信息）。 */
  description: ReactNode
  /** 确认按钮文字，默认“确认”。 */
  confirmText?: string
  /** 取消按钮文字，默认“取消”。 */
  cancelText?: string
  /** 是否为危险操作（使用危险色按钮）。 */
  danger?: boolean
  /** 确认按钮加载态。 */
  loading?: boolean
  /** 确认回调。 */
  onConfirm: () => void
  /** 取消回调。 */
  onCancel: () => void
}

/** 二次确认对话框。 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  danger = false,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const footer = (
    <div className={styles.footer}>
      <Button variant="secondary" onClick={onCancel} disabled={loading}>
        {cancelText}
      </Button>
      <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
        {confirmText}
      </Button>
    </div>
  )
  return (
    <Modal open={open} title={title} size="small" onClose={onCancel} footer={footer}>
      <div className={styles.description}>{description}</div>
    </Modal>
  )
}

export default ConfirmDialog
