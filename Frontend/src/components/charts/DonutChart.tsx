/**
 * 环形图：纯 SVG 手写，用 strokeDasharray 分段绘制，灰阶透明度区分数据项。
 * 中心可显示说明文字，图例展示标签、数值与占比。
 */

import styles from './DonutChart.module.css'

/** 环形图数据项。 */
export interface DonutChartDataItem {
  /** 分类标签。 */
  label: string
  /** 数值。 */
  value: number
}

/** 环形图属性。 */
export interface DonutChartProps {
  /** 数据项列表。 */
  data: DonutChartDataItem[]
  /** 图形尺寸（像素），默认 180。 */
  size?: number
  /** 圆心文字（不传时显示总数）。 */
  centerLabel?: string
}

/** 圆环线宽。 */
const RING_WIDTH = 14

/** 根据序号计算灰阶透明度，形成深浅层次。 */
function resolveSegmentOpacity(index: number): number {
  return Math.max(0.1, 1 - index * 0.16)
}

/** 环形图组件。 */
export function DonutChart({ data, size = 180, centerLabel }: DonutChartProps) {
  const totalValue = data.reduce((sum, item) => sum + Math.max(0, item.value), 0)
  if (data.length === 0 || totalValue <= 0) {
    return <div className={styles.empty}>No data yet</div>
  }
  const centerPoint = size / 2
  const radius = size / 2 - RING_WIDTH / 2 - 2
  const circumference = 2 * Math.PI * radius
  let accumulatedLength = 0

  return (
    <div className={styles.chart}>
      <svg
        className={styles.svg}
        viewBox={'0 0 ' + size + ' ' + size}
        role="img"
        aria-label="Donut chart"
        style={{ width: size, height: size }}
      >
        <circle
          cx={centerPoint}
          cy={centerPoint}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={RING_WIDTH}
        />
        {data.map((item, index) => {
          const safeValue = Math.max(0, item.value)
          const segmentLength = (safeValue / totalValue) * circumference
          const segmentOffset = accumulatedLength
          accumulatedLength += segmentLength
          return (
            <circle
              key={item.label + '-' + index}
              cx={centerPoint}
              cy={centerPoint}
              r={radius}
              fill="none"
              stroke="var(--color-text)"
              strokeOpacity={resolveSegmentOpacity(index)}
              strokeWidth={RING_WIDTH}
              strokeDasharray={segmentLength + ' ' + Math.max(0, circumference - segmentLength)}
              strokeDashoffset={-segmentOffset}
              transform={'rotate(-90 ' + centerPoint + ' ' + centerPoint + ')'}
            >
              <title>{item.label + '：' + item.value}</title>
            </circle>
          )
        })}
        <text
          x={centerPoint}
          y={centerPoint}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size >= 160 ? 16 : 13}
          fill="var(--color-text)"
        >
          {centerLabel ?? totalValue}
        </text>
      </svg>
      <ul className={styles.legend}>
        {data.map((item, index) => {
          const percentage = Math.round((Math.max(0, item.value) / totalValue) * 100)
          return (
            <li key={item.label + '-legend-' + index} className={styles.legendItem}>
              <span
                className={styles.legendSwatch}
                style={{ opacity: resolveSegmentOpacity(index) }}
              />
              <span className={styles.legendLabel}>{item.label}</span>
              <span className={styles.legendValue}>
                {item.value}（{percentage}%）
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default DonutChart
