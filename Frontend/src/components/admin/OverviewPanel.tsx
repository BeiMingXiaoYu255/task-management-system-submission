/**
 * 管理后台概览面板：展示用户、团队、任务等全局统计指标。
 * 纯展示组件，数据来自 adminApi.getAdminOverview。
 */

import { useCallback, useEffect, useState } from 'react'

import { getAdminOverview } from '../../api/adminApi'
import type { AdminOverview } from '../../types/admin'
import Button from '../ui/Button'
import Card from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import styles from './OverviewPanel.module.css'

/** 概览指标配置。 */
interface OverviewMetric {
  key: keyof Omit<AdminOverview, 'databaseName'>
  label: string
  description: string
}

/** 概览指标列表。 */
const OVERVIEW_METRICS: OverviewMetric[] = [
  { key: 'userCount', label: 'Total Users', description: 'All registered users in the system' },
  { key: 'activeUserCount', label: 'Active Users', description: 'Users currently enabled' },
  { key: 'teamCount', label: 'Total Teams', description: 'All teams in the system' },
  { key: 'pendingTeamCount', label: 'Teams Pending Certification', description: 'Awaiting administrator review' },
  { key: 'taskCount', label: 'Total Tasks', description: 'All published tasks in the system' },
]

/** 管理后台概览面板。 */
export default function OverviewPanel() {
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 加载全局概览数据。 */
  const loadOverview = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const adminOverview = await getAdminOverview()
      setOverview(adminOverview)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load overview data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  if (loading) {
    return (
      <div className={styles.stateArea}>
        <Spinner />
        <span>Loading overview data ...</span>
      </div>
    )
  }

  if (errorMessage !== null || overview === null) {
    return (
      <EmptyState
        title="Failed to load overview"
        description={errorMessage ?? 'Overview data unavailable'}
        action={
          <Button variant="secondary" onClick={() => void loadOverview()}>
            Reload
          </Button>
        }
      />
    )
  }

  return (
    <div className={styles.overviewLayout}>
      <div className={styles.metricGrid}>
        {OVERVIEW_METRICS.map((metric) => (
          <Card key={metric.key} className={styles.metricCard}>
            <div className={styles.metricContent}>
              <span className={styles.metricLabel}>{metric.label}</span>
              <span className={styles.metricValue}>{overview[metric.key]}</span>
              <span className={styles.metricDescription}>{metric.description}</span>
            </div>
          </Card>
        ))}
      </div>
      <Card title="Database Information">
        <div className={styles.databaseRow}>
          <span className={styles.metricLabel}>Current Database</span>
          <span className={styles.databaseName}>{overview.databaseName}</span>
        </div>
      </Card>
    </div>
  )
}
