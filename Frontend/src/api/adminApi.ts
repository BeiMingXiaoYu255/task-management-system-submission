/** 管理后台接口调用（仅全局管理员/超级用户）。 */

import type { PageResult } from '../types/common'
import type {
  AdminOverview,
  AdminTeamItem,
  AdminUserItem,
  AuditLogItem,
  DatabaseRowsResult,
  DatabaseTableInfo,
  ExecuteSqlResult,
} from '../types/admin'
import { request } from './httpClient'

/** 用户管理分页列表。 */
export function listAdminUsers(query: {
  keyword?: string
  globalRole?: string
  isActive?: boolean
  page?: number
  pageSize?: number
}): Promise<PageResult<AdminUserItem>> {
  return request<PageResult<AdminUserItem>>('/admin/users', { query: { ...query } })
}

/** 设置/取消全局管理员（仅超级用户）。 */
export function setGlobalRole(userId: number, globalRole: 'globalAdmin' | 'user'): Promise<AdminUserItem> {
  return request<AdminUserItem>('/admin/users/' + userId + '/global-role', {
    method: 'PUT',
    body: { globalRole },
  })
}

/** 启用/禁用用户账号。 */
export function setUserStatus(userId: number, isActive: boolean): Promise<AdminUserItem> {
  return request<AdminUserItem>('/admin/users/' + userId + '/status', {
    method: 'PUT',
    body: { isActive },
  })
}

/** 团队管理分页列表。 */
export function listAdminTeams(query: {
  keyword?: string
  status?: string
  page?: number
  pageSize?: number
}): Promise<PageResult<AdminTeamItem>> {
  return request<PageResult<AdminTeamItem>>('/admin/teams', { query: { ...query } })
}

/** 团队认证审核。 */
export function certifyTeam(teamId: number, approved: boolean): Promise<AdminTeamItem> {
  return request<AdminTeamItem>('/admin/teams/' + teamId + '/certification', {
    method: 'PUT',
    body: { approved },
  })
}

/** 数据库表清单。 */
export function listDatabaseTables(): Promise<DatabaseTableInfo[]> {
  return request<DatabaseTableInfo[]>('/admin/database/tables')
}

/** 浏览表数据。 */
export function getDatabaseRows(
  tableName: string,
  page: number,
  pageSize: number,
): Promise<DatabaseRowsResult> {
  return request<DatabaseRowsResult>('/admin/database/tables/' + tableName + '/rows', {
    query: { page, pageSize },
  })
}

/** 执行单条 DML SQL。 */
export function executeSql(sql: string): Promise<ExecuteSqlResult> {
  return request<ExecuteSqlResult>('/admin/database/execute', {
    method: 'POST',
    body: { sql, confirm: true },
  })
}

/** 审计日志分页列表。 */
export function listAuditLogs(query: {
  page?: number
  pageSize?: number
}): Promise<PageResult<AuditLogItem>> {
  return request<PageResult<AuditLogItem>>('/admin/audit-logs', { query: { ...query } })
}

/** 管理后台概览数据。 */
export function getAdminOverview(): Promise<AdminOverview> {
  return request<AdminOverview>('/admin/overview')
}
