/**
 * 柱状图：纯 SVG 手写，颜色全部取自 CSS 变量，随深浅主题自动切换。
 * 适用于优先级分布、状态分布等单序列数据。
 */

import styles from './BarChart.module.css'

/** 柱状图数据项。 */
export interface BarChartDataItem {
  /** 分类标签。 */
  label: string
  /** 数值。 */
  value: number
}

/** 柱状图属性。 */
export interface BarChartProps {
  /** 数据项列表。 */
  data: BarChartDataItem[]
  /** 图表高度（像素），默认 240。 */
  height?: number
}

/** SVG 画布逻辑宽度，实际渲染宽度由容器决定。 */
const VIEWBOX_WIDTH = 640

/** 画布内边距。 */
const CHART_PADDING = { top: 24, right: 8, bottom: 36, left: 8 }

/** 截断过长标签，避免文字重叠。 */
function shortenLabel(label: string, maxLength = 7): string {
  return label.length > maxLength ? label.slice(0, maxLength - 1) + '…' : label
}

/** 柱状图组件。 */
export function BarChart({ data, height = 240 }: BarChartProps) {
  if (data.length === 0) {
    return <div className={styles.empty}>No data yet</div>
  }
  const maxValue = Math.max(1, ...data.map((item) => item.value))
  const innerWidth = VIEWBOX_WIDTH - CHART_PADDING.left - CHART_PADDING.right
  const innerHeight = height - CHART_PADDING.top - CHART_PADDING.bottom
  const slotWidth = innerWidth / data.length
  const barWidth = Math.min(44, Math.max(8, slotWidth * 0.55))
  const baselineY = CHART_PADDING.top + innerHeight
  const gridRatios = [0, 0.5, 1]

  return (
    <div className={styles.chart}>
      <svg className={styles.svg} viewBox={'0 0 ' + VIEWBOX_WIDTH + ' ' + height} role="img" aria-label="Bar chart">
        {gridRatios.map((ratio) => {
          const lineY = CHART_PADDING.top + innerHeight * (1 - ratio)
          return (
            <line
              key={'grid-' + ratio}
              x1={CHART_PADDING.left}
              y1={lineY}
              x2={VIEWBOX_WIDTH - CHART_PADDING.right}
              y2={lineY}
              stroke={ratio === 0 ? 'var(--color-border-strong)' : 'var(--color-border)'}
              strokeWidth={1}
            />
          )
        })}
        {data.map((item, index) => {
          const barHeight = item.value <= 0 ? 0 : (item.value / maxValue) * innerHeight
          const slotCenterX = CHART_PADDING.left + slotWidth * index + slotWidth / 2
          const barX = slotCenterX - barWidth / 2
          const barY = baselineY - barHeight
          return (
            <g key={item.label + '-' + index}>
              <title>{item.label + '：' + item.value}</title>
              <rect x={barX} y={barY} width={barWidth} height={barHeight} fill="var(--color-inverse-bg)" />
              <text
                x={slotCenterX}
                y={barY - 6}
                textAnchor="middle"
                fontSize={11}
                fill="var(--color-text-secondary)"
              >
                {item.value}
              </text>
              <text
                x={slotCenterX}
                y={baselineY + 18}
                textAnchor="middle"
                fontSize={11}
                fill="var(--color-text-secondary)"
              >
                {shortenLabel(item.label)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export default BarChart
