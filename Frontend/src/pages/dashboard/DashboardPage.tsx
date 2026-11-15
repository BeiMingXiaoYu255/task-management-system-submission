/**
 * 仪表盘页面：聚合展示待办、审核、归档等核心指标，并给出团队维度统计。
 *
 * 页面职责：
 * 1. 通过 dashboardApi.getDashboardSummary 获取汇总数据；
 * 2. 维护团队筛选状态（默认聚合全部团队）；
 * 3. 处理加载中、加载失败与空数据三种状态；
 * 4. 具体展示逻辑拆分到 components/dashboard 下的纯展示组件。
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { getDashboardSummary } from '../../api/dashboardApi'
import DistributionPanels from '../../components/dashboard/DistributionPanels'
import StatCards from '../../components/dashboard/StatCards'
import TeamStatsTable from '../../components/dashboard/TeamStatsTable'
import TrendPanel from '../../components/dashboard/TrendPanel'
import Button from '../../components/ui/Button'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Select from '../../components/ui/Select'
import Spinner from '../../components/ui/Spinner'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import type { DashboardSummary } from '../../types/dashboard'
import styles from './DashboardPage.module.css'

/** 团队筛选的“全部团队”取值。 */
const ALL_TEAMS_VALUE = 0

/** 仪表盘页面。 */
export default function DashboardPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [selectedTeamId, setSelectedTeamId] = useState<number>(ALL_TEAMS_VALUE)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 团队筛选下拉选项：第一项为全部团队。 */
  const teamOptions = useMemo(() => {
    const options: { value: number; label: string }[] = [{ value: ALL_TEAMS_VALUE, label: 'All Teams' }]
    const memberships = user?.teams ?? []
    memberships.forEach((membership) => {
      options.push({ value: membership.teamId, label: membership.teamName })
    })
    return options
  }, [user])

  /** 拉取仪表盘汇总数据；筛选变化时重新拉取。 */
  const loadSummary = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const teamId = selectedTeamId === ALL_TEAMS_VALUE ? undefined : selectedTeamId
      const dashboardSummary = await getDashboardSummary(teamId)
      setSummary(dashboardSummary)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load dashboard data'
      setErrorMessage(message)
    } finally {
      setLoading(false)
    }
  }, [selectedTeamId])

  useEffect(() => {
    void loadSummary()
  }, [loadSummary])

  /** 团队筛选变化：切换后自动重新加载。 */
  const handleTeamChange = (value: string | number): void => {
    setSelectedTeamId(Number(value))
  }

  /** 渲染主体内容：按加载/错误/数据三种状态分支。 */
  const renderContent = (): ReactNode => {
    if (loading) {
      return (
        <div className={styles.stateArea}>
          <Spinner />
          <span className={styles.stateText}>Loading dashboard data ...</span>
        </div>
      )
    }
    if (errorMessage !== null) {
      return (
        <EmptyState
          title="Failed to load data"
          description={errorMessage}
          action={
            <Button variant="secondary" onClick={() => void loadSummary()}>
              Reload
            </Button>
          }
        />
      )
    }
    if (summary === null) {
      return <EmptyState title="No data yet" description="No statistics available for the current filter." />
    }
    return (
      <div className={styles.contentStack}>
        <StatCards summary={summary} />
        <DistributionPanels byPriority={summary.byPriority} byStatus={summary.byStatus} />
        <TrendPanel weeklyTrend={summary.weeklyTrend} />
        <TeamStatsTable teamStats={summary.teamStats} />
      </div>
    )
  }

  return (
    <div className={styles.pageRoot}>
      <PageHeader
        title="Dashboard"
        description="Track to-do progress and overall team output. All teams are included by default."
        actions={
          <div className={styles.filterArea}>
            <span className={styles.filterLabel}>Team Filter</span>
            <Select
              value={selectedTeamId}
              onChange={handleTeamChange}
              options={teamOptions}
              placeholder="Select a team"
            />
          </div>
        }
      />
      {renderContent()}
    </div>
  )
}
