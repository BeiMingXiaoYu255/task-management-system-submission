/**
 * 仪表盘统计卡片组：集中展示五项核心指标。
 * 纯展示组件，不发起请求、不持有业务状态。
 */

import type { DashboardSummary } from '../../types/dashboard'
import Card from '../ui/Card'
import styles from './StatCards.module.css'

/** 单张统计卡片的配置。 */
interface StatCardConfig {
  /** 卡片唯一标识。 */
  key: string
  /** 指标名称。 */
  label: string
  /** 指标数值。 */
  value: number
  /** 指标说明文字。 */
  description: string
  /** 是否使用危险态强调（如逾期）。 */
  danger: boolean
}

/** 统计卡片组属性。 */
interface StatCardsProps {
  summary: DashboardSummary
}

/** 统计卡片组：待办 / 待审核 / 本周完成 / 逾期 / 累计归档。 */
export default function StatCards({ summary }: StatCardsProps) {
  const cardItems: StatCardConfig[] = [
    {
      key: 'todoCount',
      label: 'To-do Tasks',
      value: summary.todoCount,
      description: 'Total tasks requiring your action',
      danger: false,
    },
    {
      key: 'pendingReviewCount',
      label: 'Pending Review',
      value: summary.pendingReviewCount,
      description: 'Submitted and awaiting review',
      danger: false,
    },
    {
      key: 'archivedThisWeek',
      label: 'Completed This Week',
      value: summary.archivedThisWeek,
      description: 'Tasks archived this week',
      danger: false,
    },
    {
      key: 'overdueCount',
      label: 'Overdue Tasks',
      value: summary.overdueCount,
      description: 'Past the due date',
      danger: true,
    },
    {
      key: 'archivedTotal',
      label: 'Total Archived',
      value: summary.archivedTotal,
      description: 'Total tasks archived in history',
      danger: false,
    },
  ]

  return (
    <div className={styles.cardGrid}>
      {cardItems.map((cardItem) => (
        <Card key={cardItem.key} className={styles.statCard}>
          <div className={styles.statContent}>
            <span className={styles.statLabel}>{cardItem.label}</span>
            <span
              className={
                cardItem.danger && cardItem.value > 0 ? styles.statValueDanger : styles.statValue
              }
            >
              {cardItem.value}
            </span>
            <span className={styles.statDescription}>{cardItem.description}</span>
          </div>
        </Card>
      ))}
    </div>
  )
}
