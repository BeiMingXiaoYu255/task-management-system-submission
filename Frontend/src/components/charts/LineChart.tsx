/**
 * 折线图：纯 SVG 手写，支持多序列，用灰阶透明度区分序列。
 * 颜色全部取自 CSS 变量，随深浅主题自动切换。
 */

import styles from './LineChart.module.css'

/** 折线序列。 */
export interface LineChartSeries {
  /** 序列名称（用于图例）。 */
  label: string
  /** 序列数值，长度应与 labels 一致。 */
  values: number[]
}

/** 折线图属性。 */
export interface LineChartProps {
  /** 序列列表。 */
  data: LineChartSeries[]
  /** 横轴标签列表。 */
  labels: string[]
  /** 图表高度（像素），默认 240。 */
  height?: number
}

/** SVG 画布逻辑宽度。 */
const VIEWBOX_WIDTH = 640

/** 画布内边距。 */
const CHART_PADDING = { top: 20, right: 16, bottom: 32, left: 16 }

/** 多序列使用的灰阶透明度（主题安全，不依赖具体色值）。 */
const SERIES_OPACITY = [1, 0.55, 0.32, 0.2, 0.12]

/** 折线图组件。 */
export function LineChart({ data, labels, height = 240 }: LineChartProps) {
  if (data.length === 0 || labels.length === 0) {
    return <div className={styles.empty}>No data yet</div>
  }
  const allValues = data.flatMap((series) => series.values)
  const maxValue = Math.max(1, ...allValues)
  const innerWidth = VIEWBOX_WIDTH - CHART_PADDING.left - CHART_PADDING.right
  const innerHeight = height - CHART_PADDING.top - CHART_PADDING.bottom
  const baselineY = CHART_PADDING.top + innerHeight
  const pointCount = labels.length
  const stepX = pointCount > 1 ? innerWidth / (pointCount - 1) : 0
  const gridRatios = [0, 0.25, 0.5, 0.75, 1]
  /** 标签过多时按间隔抽稀，避免横向重叠。 */
  const labelStep = Math.max(1, Math.ceil(pointCount / 10))

  /** 计算第 index 个点的横坐标。 */
  const resolvePointX = (index: number): number => {
    if (pointCount === 1) {
      return CHART_PADDING.left + innerWidth / 2
    }
    return CHART_PADDING.left + stepX * index
  }

  return (
    <div className={styles.chart}>
      <svg className={styles.svg} viewBox={'0 0 ' + VIEWBOX_WIDTH + ' ' + height} role="img" aria-label="Line chart">
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
        {data.map((series, seriesIndex) => {
          const opacity = SERIES_OPACITY[seriesIndex] ?? 0.1
          const points = series.values
            .map((value, index) => {
              const pointX = resolvePointX(index)
              const pointY = baselineY - (Math.max(0, value) / maxValue) * innerHeight
              return pointX + ',' + pointY
            })
            .join(' ')
          return (
            <g key={series.label + '-' + seriesIndex}>
              <title>{series.label}</title>
              <polyline
                points={points}
                fill="none"
                stroke="var(--color-text)"
                strokeOpacity={opacity}
                strokeWidth={1.6}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {series.values.map((value, index) => {
                const pointX = resolvePointX(index)
                const pointY = baselineY - (Math.max(0, value) / maxValue) * innerHeight
                return (
                  <circle
                    key={'point-' + index}
                    cx={pointX}
                    cy={pointY}
                    r={2.2}
                    fill="var(--color-text)"
                    fillOpacity={opacity}
                  />
                )
              })}
            </g>
          )
        })}
        {labels.map((label, index) => {
          if (index % labelStep !== 0 && index !== labels.length - 1) {
            return null
          }
          return (
            <text
              key={label + '-' + index}
              x={resolvePointX(index)}
              y={height - 10}
              textAnchor="middle"
              fontSize={11}
              fill="var(--color-text-secondary)"
            >
              {label}
            </text>
          )
        })}
      </svg>
      <div className={styles.legend}>
        {data.map((series, seriesIndex) => (
          <span key={series.label + '-' + seriesIndex} className={styles.legendItem}>
            <span
              className={styles.legendSwatch}
              style={{ opacity: SERIES_OPACITY[seriesIndex] ?? 0.1 }}
            />
            <span>{series.label}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default LineChart
