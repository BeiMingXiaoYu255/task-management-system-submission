/** 仪表盘数据类型。 */

/** 按维度统计项。 */
export interface CountItem {
  priority?: string
  status?: string
  count: number
}

/** 一周趋势项。 */
export interface TrendItem {
  date: string
  created: number
  completed: number
}

/** 团队统计项。 */
export interface TeamStatItem {
  teamId: number
  teamName: string
  memberCount: number
  openTaskCount: number
  archivedTaskCount: number
}

/** 仪表盘汇总数据。 */
export interface DashboardSummary {
  todoCount: number
  pendingAcceptanceCount: number
  inProgressCount: number
  pendingReviewCount: number
  archivedThisWeek: number
  overdueCount: number
  archivedTotal: number
  byPriority: { priority: string; count: number }[]
  byStatus: { status: string; count: number }[]
  weeklyTrend: TrendItem[]
  teamStats: TeamStatItem[]
}
