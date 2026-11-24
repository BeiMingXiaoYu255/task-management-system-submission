/**
 * 下拉菜单：点击触发器展开菜单，支持点击外部与 Esc 关闭。
 * 触发器由调用方传入任意 ReactNode（通常是文字或按钮）。
 */

import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

import styles from './Dropdown.module.css'

/** 下拉菜单项。 */
export interface DropdownItem {
  /** 唯一键。 */
  key: string
  /** 显示文本。 */
  label: string
  /** 是否为危险操作（使用危险色文字）。 */
  danger?: boolean
  /** 是否禁用。 */
  disabled?: boolean
  /** 点击回调。 */
  onClick: () => void
}

/** 下拉菜单位置。 */
export type DropdownAlign = 'left' | 'right'

/** 下拉菜单属性。 */
export interface DropdownProps {
  /** 触发器内容。 */
  trigger: ReactNode
  /** 菜单项列表。 */
  items: DropdownItem[]
  /** 菜单展开方向，默认 right（右对齐）。 */
  align?: DropdownAlign
  /** 额外样式类名。 */
  className?: string
}

/** 下拉菜单组件。 */
export function Dropdown({ trigger, items, align = 'right', className }: DropdownProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLSpanElement | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    /** 点击菜单外部时关闭。 */
    const handleDocumentMouseDown = (event: MouseEvent): void => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    /** Esc 键关闭。 */
    const handleDocumentKeyDown = (event: globalThis.KeyboardEvent): void => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleDocumentMouseDown)
    document.addEventListener('keydown', handleDocumentKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleDocumentMouseDown)
      document.removeEventListener('keydown', handleDocumentKeyDown)
    }
  }, [open])

  /** 触发器键盘操作：Enter/空格切换，Esc 关闭。 */
  const handleTriggerKeyDown = (event: KeyboardEvent<HTMLSpanElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setOpen((previous) => !previous)
    }
    if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const classNames = [styles.dropdown]
  if (className) {
    classNames.push(className)
  }
  const menuClassNames = [styles.menu, align === 'left' ? styles.menuLeft : styles.menuRight]

  return (
    <span className={classNames.join(' ')} ref={containerRef}>
      <span
        className={styles.trigger}
        role="button"
        tabIndex={0}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        onKeyDown={handleTriggerKeyDown}
      >
        {trigger}
      </span>
      {open ? (
        <span className={menuClassNames.join(' ')} role="menu">
          {items.map((item) => {
            const itemClassNames = [styles.menuItem]
            if (item.danger) {
              itemClassNames.push(styles.dangerItem)
            }
            return (
              <button
                key={item.key}
                type="button"
                role="menuitem"
                className={itemClassNames.join(' ')}
                disabled={item.disabled}
                onClick={() => {
                  setOpen(false)
                  item.onClick()
                }}
              >
                {item.label}
              </button>
            )
          })}
        </span>
      ) : null}
    </span>
  )
}

export default Dropdown
