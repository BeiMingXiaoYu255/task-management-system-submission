/**
 * 轻提示上下文：全局显示操作成功/失败提示，3 秒后自动消失。
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

import styles from './ToastContext.module.css'

/** 提示类型。 */
export type ToastType = 'info' | 'success' | 'error'

/** 单条提示数据。 */
interface ToastItem {
  id: number
  message: string
  type: ToastType
}

/** 提示上下文接口。 */
interface ToastContextValue {
  /** 显示一条提示。 */
  showToast: (message: string, type?: ToastType) => void
}

/** 提示上下文对象。 */
const ToastContext = createContext<ToastContextValue | null>(null)

/** 提示提供者：负责渲染提示容器。 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toastItems, setToastItems] = useState<ToastItem[]>([])
  const nextIdRef = useRef(1)

  /** 显示提示并在 3 秒后移除。 */
  const showToast = useCallback((message: string, type: ToastType = 'info'): void => {
    const toastId = nextIdRef.current
    nextIdRef.current += 1
    setToastItems((previous) => [...previous, { id: toastId, message, type }])
    window.setTimeout(() => {
      setToastItems((previous) => previous.filter((item) => item.id !== toastId))
    }, 3000)
  }, [])

  const contextValue = useMemo<ToastContextValue>(() => ({ showToast }), [showToast])

  /** 根据类型返回提示样式类名。 */
  const resolveToastClassName = (type: ToastType): string => {
    if (type === 'error') {
      return styles.toastItem + ' ' + styles.toastError
    }
    if (type === 'success') {
      return styles.toastItem + ' ' + styles.toastSuccess
    }
    return styles.toastItem
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className={styles.toastContainer}>
        {toastItems.map((item) => (
          <div key={item.id} className={resolveToastClassName(item.type)} role="status">
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

/** 读取提示上下文；必须在 ToastProvider 内使用。 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (context === null) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
