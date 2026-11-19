/**
 * 协作导航图标：两个相连的单位方框，与布局图标保持同一视觉规格。
 *
 * 该图标仅用于侧边栏「协作」入口，颜色随父级 currentColor 变化。
 */

import type { LayoutIconProps } from '../layout/LayoutIcons'

/** 协作导航图标。 */
export function CollaborationNavIcon({ size = 16, className }: LayoutIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="2.5" y="4.5" width="6" height="11" rx="1" />
      <rect x="11.5" y="4.5" width="6" height="11" rx="1" />
      <path d="M8.5 10H11.5" />
      <path d="M6.5 8V7" />
      <path d="M13.5 8V7" />
    </svg>
  )
}

export default CollaborationNavIcon
