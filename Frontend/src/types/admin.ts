/** 管理后台类型。 */

import type { DateTimeString, GlobalRole, TeamStatus } from './common'

/** 管理后台用户列表项。 */
export interface AdminUserItem {
  id: number
  username: string
  nickname: string
  email: string | null
  globalRole: GlobalRole
  isActive: boolean
  teamCount: number
  createdAt: DateTimeString
}

/** 管理后台团队列表项。 */
export interface AdminTeamItem {
  id: number
  name: string
  status: TeamStatus
  joinMethod: string
  createdBy: number | null
  creatorName: string
  memberCount: number
  taskCount: number
  createdAt: DateTimeString
}

/** 数据库表信息。 */
export interface DatabaseTableInfo {
  tableName: string
  rowCount: number
}

/** 数据库表数据浏览结果。 */
export interface DatabaseRowsResult {
  tableName: string
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  page: number
  pageSize: number
}

/** 执行 SQL 的结果。 */
export interface ExecuteSqlResult {
  executed: boolean
  statementType: string
  affectedRows: number
  rows: Record<string, unknown>[]
}

/** 审计日志项。 */
export interface AuditLogItem {
  id: number
  userId: number | null
  operatorName: string
  action: string
  detail: string | null
  ip: string | null
  createdAt: DateTimeString
}

/** 管理后台概览数据。 */
export interface AdminOverview {
  userCount: number
  activeUserCount: number
  teamCount: number
  pendingTeamCount: number
  taskCount: number
  databaseName: string
}
