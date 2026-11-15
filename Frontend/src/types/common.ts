/** 通用类型：分页结构、枚举字面量、请求参数。 */

/** 统一分页响应结构。 */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/** 全局角色。 */
export type GlobalRole = 'superAdmin' | 'globalAdmin' | 'user'

/** 团队角色。 */
export type TeamRole = 'admin' | 'subAdmin' | 'member'

/** 团队加入方式。 */
export type JoinMethod = 'free' | 'approval' | 'inviteOnly'

/** 团队认证状态。 */
export type TeamStatus = 'pending' | 'active' | 'rejected'

/** 任务优先级。 */
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

/** 任务聚合状态。 */
export type TaskStatus = 'published' | 'inProgress' | 'pendingReview' | 'archived' | 'cancelled'

/** 个人待办状态。 */
export type AssignmentStatus = 'pendingAcceptance' | 'inProgress' | 'pendingReview' | 'archived'

/** 任务分配方式。 */
export type AssignmentMode = 'specific' | 'levelRange'

/** 任务接受方式。 */
export type AcceptanceMode = 'mandatory' | 'optional'

/** 列表通用查询参数。 */
export interface PageQuery {
  page?: number
  pageSize?: number
}

/** 时间字段类型别名（ISO 8601 字符串）。 */
export type DateTimeString = string

/** 简单消息响应。 */
export interface MessageResponse {
  message: string
}
