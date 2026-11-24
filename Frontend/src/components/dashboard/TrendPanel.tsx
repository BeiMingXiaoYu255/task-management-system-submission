/**
 * 仪表盘趋势面板：用折线图展示近 7 天任务创建与完成数量。
 * 图表横轴为日期（MM-DD），纵轴为任务数；无数据时展示空态。
 */

import type { TrendItem } from '../../types/dashboard'
import LineChart from '../charts/LineChart'
import Card from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import styles from './TrendPanel.module.css'

/** 趋势面板属性。 */
interface TrendPanelProps {
  weeklyTrend: TrendItem[]
}

/** 近 7 天创建 / 完成趋势面板。 */
export default function TrendPanel({ weeklyTrend }: TrendPanelProps) {
  const dateLabels = weeklyTrend.map((trendItem) => trendItem.date.slice(5))
  const chartSeries = [
    { label: 'Created', values: weeklyTrend.map((trendItem) => trendItem.created) },
    { label: 'Completed', values: weeklyTrend.map((trendItem) => trendItem.completed) },
  ]

  return (
    <Card title="Created / Completed Trend (Last 7 Days)">
      <div className={styles.panelBody}>
        {weeklyTrend.length > 0 ? (
          <LineChart data={chartSeries} labels={dateLabels} height={240} />
        ) : (
          <EmptyState title="No trend data yet" description="No task records in the current scope over the last 7 days." />
        )}
      </div>
    </Card>
  )
}
