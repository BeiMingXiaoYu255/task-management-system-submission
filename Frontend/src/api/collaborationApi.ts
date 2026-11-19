/**
 * 团队协作接口调用：协作目录、协作申请、协作任务与双审核。
 *
 * 接口契约见 docs/development/collaborationContract.md 第 4.2 节；
 * 所有请求统一走 httpClient，错误由调用方捕获后展示中文提示。
 */

import type { PageQuery, PageResult } from '../types/common'
import type {
  CollaborationDirectoryItem,
  CollaborationItem,
  CollaborationQuery,
  CollaborationTaskDetail,
  CollaborationTaskItem,
  ConfirmCollaborationPayload,
  ConfirmCollaborationTaskPayload,
  CreateCollaborationPayload,
  CreateCollaborationTaskPayload,
  ReviewCollaborationTaskPayload,
} from '../types/collaboration'
import { request } from './httpClient'

/** 可申请协作的团队/子团队目录（仅已认证团队）。 */
export function getCollaborationDirectory(): Promise<CollaborationDirectoryItem[]> {
  return request<CollaborationDirectoryItem[]>('/collaboration/directory')
}

/** 发起协作申请（发起单位管理员），返回 pending 状态的协作关系。 */
export function createCollaboration(
  payload: CreateCollaborationPayload,
): Promise<CollaborationItem> {
  return request<CollaborationItem>('/collaborations', { method: 'POST', body: payload })
}

/** 与我相关的协作分页列表（我管理的单位或我作为对接人）。 */
export function listCollaborations(
  query: CollaborationQuery = {},
): Promise<PageResult<CollaborationItem>> {
  return request<PageResult<CollaborationItem>>('/collaborations', { query: { ...query } })
}

/** 协作详情（参与单位成员可见）。 */
export function getCollaboration(collaborationId: number): Promise<CollaborationItem> {
  return request<CollaborationItem>('/collaborations/' + String(collaborationId))
}

/** 接收方管理员确认或拒绝协作申请。 */
export function confirmCollaboration(
  collaborationId: number,
  payload: ConfirmCollaborationPayload,
): Promise<CollaborationItem> {
  return request<CollaborationItem>('/collaborations/' + String(collaborationId) + '/confirm', {
    method: 'POST',
    body: payload,
  })
}

/** 结束已生效的协作（任一单位管理员）。 */
export function endCollaboration(
  collaborationId: number,
  comment?: string | null,
): Promise<CollaborationItem> {
  return request<CollaborationItem>('/collaborations/' + String(collaborationId) + '/end', {
    method: 'POST',
    body: { comment: comment ?? null },
  })
}

/** 协作任务分页列表。 */
export function listCollaborationTasks(
  collaborationId: number,
  query: PageQuery = {},
): Promise<PageResult<CollaborationTaskItem>> {
  return request<PageResult<CollaborationTaskItem>>(
    '/collaborations/' + String(collaborationId) + '/tasks',
    { query: { ...query } },
  )
}

/** 新建协作任务（发起方管理员或发起方对接人）。 */
export function createCollaborationTask(
  collaborationId: number,
  payload: CreateCollaborationTaskPayload,
): Promise<CollaborationTaskItem> {
  return request<CollaborationTaskItem>('/collaborations/' + String(collaborationId) + '/tasks', {
    method: 'POST',
    body: payload,
  })
}

/** 协作任务详情（参与单位成员可见，含双审核权限标记与审核记录）。 */
export function getCollaborationTask(taskId: number): Promise<CollaborationTaskDetail> {
  return request<CollaborationTaskDetail>('/collaboration-tasks/' + String(taskId))
}

/** 接收方对接人确认接单并指派执行人，或拒绝任务。 */
export function confirmCollaborationTask(
  taskId: number,
  payload: ConfirmCollaborationTaskPayload,
): Promise<CollaborationTaskItem> {
  return request<CollaborationTaskItem>('/collaboration-tasks/' + String(taskId) + '/confirm', {
    method: 'POST',
    body: payload,
  })
}

/** 接收方对接人审核（接收方审核阶段）。 */
export function reviewCollaborationTaskAsTarget(
  taskId: number,
  payload: ReviewCollaborationTaskPayload,
): Promise<CollaborationTaskItem> {
  return request<CollaborationTaskItem>(
    '/collaboration-tasks/' + String(taskId) + '/target-review',
    { method: 'POST', body: payload },
  )
}

/** 发起方发布者/管理员审核（发起方审核阶段）。 */
export function reviewCollaborationTaskAsSource(
  taskId: number,
  payload: ReviewCollaborationTaskPayload,
): Promise<CollaborationTaskItem> {
  return request<CollaborationTaskItem>(
    '/collaboration-tasks/' + String(taskId) + '/source-review',
    { method: 'POST', body: payload },
  )
}