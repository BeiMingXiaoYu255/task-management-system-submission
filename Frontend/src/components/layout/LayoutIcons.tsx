/**
 * 布局内联 SVG 图标集合：统一 20x20 视窗、1.4 线宽、currentColor 描边。
 * 不依赖任何图标库，颜色随父级文字颜色与主题自动变化。
 */

import styles from './LayoutIcons.module.css'

/** 图标通用属性。 */
export interface LayoutIconProps {
  /** 图形尺寸（像素），默认 16。 */
  size?: number
  /** 额外样式类名。 */
  className?: string
}

/** 创建统一规格的 svg 容器属性，减少重复代码。 */
function buildIconAttributes({ size = 16, className }: LayoutIconProps) {
  return {
    width: size,
    height: size,
    viewBox: '0 0 20 20',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.4,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className: [styles.icon, className].filter(Boolean).join(' '),
    'aria-hidden': true,
  }
}

/** 仪表盘图标（四宫格）。 */
export function IconDashboard(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <rect x="2.5" y="2.5" width="6" height="6" />
      <rect x="11.5" y="2.5" width="6" height="6" />
      <rect x="2.5" y="11.5" width="6" height="6" />
      <rect x="11.5" y="11.5" width="6" height="6" />
    </svg>
  )
}

/** 团队图标（两个人形）。 */
export function IconTeam(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <circle cx="7.5" cy="6.5" r="2.5" />
      <path d="M2.5 16.5C2.5 13.5 4.7 12 7.5 12C10.3 12 12.5 13.5 12.5 16.5" />
      <circle cx="14" cy="7" r="2" />
      <path d="M13.5 11.6C15.9 11.8 17.5 13.2 17.5 15.5" />
    </svg>
  )
}

/** 待办图标（清单加勾）。 */
export function IconTodo(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <path d="M4 5.5L5.2 6.7L7.4 4.5" />
      <path d="M4 11L5.2 12.2L7.4 10" />
      <path d="M10.5 6H17" />
      <path d="M10.5 11.5H17" />
      <path d="M10.5 16H17" />
      <path d="M4 15.5H7.5" />
    </svg>
  )
}

/** 任务图标（带勾的方框）。 */
export function IconTask(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <rect x="2.5" y="4" width="15" height="12" rx="1" />
      <path d="M6 10L8.6 12.6L13.8 7.4" />
    </svg>
  )
}

/** 个人资料图标（单人形）。 */
export function IconProfile(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <circle cx="10" cy="6.5" r="3" />
      <path d="M4 17C4 13.9 6.6 12 10 12C13.4 12 16 13.9 16 17" />
    </svg>
  )
}

/** 设置图标（齿轮简化为圆加辐条）。 */
export function IconSettings(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <circle cx="10" cy="10" r="3.2" />
      <path d="M10 2.5V5" />
      <path d="M10 15V17.5" />
      <path d="M2.5 10H5" />
      <path d="M15 10H17.5" />
      <path d="M4.7 4.7L6.4 6.4" />
      <path d="M13.6 13.6L15.3 15.3" />
      <path d="M15.3 4.7L13.6 6.4" />
      <path d="M6.4 13.6L4.7 15.3" />
    </svg>
  )
}

/** 管理后台图标（盾牌）。 */
export function IconAdmin(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <path d="M10 2.5L16.5 5V9.5C16.5 13.5 13.8 16.2 10 17.5C6.2 16.2 3.5 13.5 3.5 9.5V5L10 2.5Z" />
      <path d="M7.2 9.8L9.2 11.8L12.9 8.1" />
    </svg>
  )
}

/** 太阳图标（浅色主题下显示，用于切换到深色）。 */
export function IconSun(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <circle cx="10" cy="10" r="3.5" />
      <path d="M10 2V3.5" />
      <path d="M10 16.5V18" />
      <path d="M2 10H3.5" />
      <path d="M16.5 10H18" />
      <path d="M4.3 4.3L5.4 5.4" />
      <path d="M14.6 14.6L15.7 15.7" />
      <path d="M15.7 4.3L14.6 5.4" />
      <path d="M5.4 14.6L4.3 15.7" />
    </svg>
  )
}

/** 月亮图标（深色主题下显示，用于切换到浅色）。 */
export function IconMoon(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <path d="M16 12.2A6.8 6.8 0 0 1 7.8 4A6.8 6.8 0 1 0 16 12.2Z" />
    </svg>
  )
}

/** 菜单图标（三条横线）。 */
export function IconMenu(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <path d="M3.5 5.5H16.5" />
      <path d="M3.5 10H16.5" />
      <path d="M3.5 14.5H16.5" />
    </svg>
  )
}

/** 复制图标（两张叠放的纸）。 */
export function IconCopy(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <rect x="7" y="7" width="10" height="10" rx="1" />
      <path d="M13 4.5V3.5C13 3 12.6 2.5 12 2.5H4C3.4 2.5 3 3 3 3.5V11.5C3 12 3.4 12.5 4 12.5H5" />
    </svg>
  )
}

/** 便签图标（折角便笺）。 */
export function IconSticky(props: LayoutIconProps) {
  return (
    <svg {...buildIconAttributes(props)}>
      <path d="M3.5 3.5H13L16.5 7V16.5H3.5V3.5Z" />
      <path d="M13 3.5V7H16.5" />
      <path d="M6.5 10H13.5" />
      <path d="M6.5 13H11.5" />
    </svg>
  )
}