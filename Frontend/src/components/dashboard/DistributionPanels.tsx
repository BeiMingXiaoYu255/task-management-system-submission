/**
 * 仪表盘分布图组：左侧为优先级分布柱状图，右侧为任务状态分布环形图。
 * 数据转换（枚举转中文）在本组件内完成，保持页面容器简洁。
 */

import type { CountItem } from '../../types/dashboard'
import { getPriorityLabel, getTaskStatusLabel } from '../../utils/displayUtils'
import BarChart from '../charts/BarChart'
import DonutChart from '../charts/DonutChart'
import Card from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import styles from './DistributionPanels.module.css'

/** 分布图组属性。 */
interface DistributionPanelsProps {
  /** 优先级维度统计。 */
  byPriority: CountItem[]
  /** 状态维度统计。 */
  byStatus: CountItem[]
}

/** 把后端枚举统计项转换为图表需要的标签数据。 */
function buildChartData(
  countItems: CountItem[],
  resolveLabel: (rawValue: string) => string,
): { label: string; value: number }[] {
  return countItems.map((countItem) => ({
    label: resolveLabel(countItem.priority ?? countItem.status ?? ''),
    value: countItem.count,
  }))
}

/** 优先级与状态分布面板。 */
export default function DistributionPanels({ byPriority, byStatus }: DistributionPanelsProps) {
  const priorityChartData = buildChartData(byPriority, getPriorityLabel)
  const statusChartData = buildChartData(byStatus, getTaskStatusLabel)
  const statusTotal = statusChartData.reduce((total, item) => total + item.value, 0)

  return (
    <div className={styles.panelGrid}>
      <Card title="Priority Distribution">
        <div className={styles.panelBody}>
          {priorityChartData.length > 0 ? (
            <BarChart data={priorityChartData} height={220} />
          ) : (
            <EmptyState title="No priority data yet" description="No tasks to summarize in the current scope." />
          )}
        </div>
      </Card>
      <Card title="Task Status Distribution">
        <div className={styles.panelBody}>
          {statusTotal > 0 ? (
            <DonutChart
              data={statusChartData}
              size={220}
              centerLabel={'Total: ' + statusTotal}
            />
          ) : (
            <EmptyState title="No status data yet" description="No tasks to summarize in the current scope." />
          )}
        </div>
      </Card>
    </div>
  )
}
