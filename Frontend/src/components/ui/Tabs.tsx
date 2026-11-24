/**
 * 页签：用于页面内部区块切换，下划线标识当前项。
 */

import styles from './Tabs.module.css'

/** 页签项。 */
export interface TabItem {
  /** 唯一键。 */
  key: string
  /** 显示文本。 */
  label: string
  /** 是否禁用。 */
  disabled?: boolean
}

/** 页签属性。 */
export interface TabsProps {
  /** 页签列表。 */
  items: TabItem[]
  /** 当前激活键。 */
  activeKey: string
  /** 切换回调。 */
  onChange: (key: string) => void
  /** 额外样式类名。 */
  className?: string
}

/** 页签组件。 */
export function Tabs({ items, activeKey, onChange, className }: TabsProps) {
  const classNames = [styles.tabs]
  if (className) {
    classNames.push(className)
  }
  return (
    <div className={classNames.join(' ')} role="tablist">
      {items.map((item) => {
        const isActive = item.key === activeKey
        const itemClassNames = [styles.tabItem]
        if (isActive) {
          itemClassNames.push(styles.activeTabItem)
        }
        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={itemClassNames.join(' ')}
            disabled={item.disabled}
            onClick={() => {
              if (!item.disabled && !isActive) {
                onChange(item.key)
              }
            }}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

export default Tabs
