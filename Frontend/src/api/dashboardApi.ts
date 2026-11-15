/** 仪表盘接口调用。 */

import type { DashboardSummary } from '../types/dashboard'
import { request } from './httpClient'

/** 获取仪表盘汇总数据；teamId 为空时聚合全部团队。 */
export function getDashboardSummary(teamId?: number): Promise<DashboardSummary> {
  return request<DashboardSummary>('/dashboard/summary', { query: { teamId } })
}
