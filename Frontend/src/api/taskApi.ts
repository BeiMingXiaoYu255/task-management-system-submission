/** 任务与审核接口调用。 */

import type { PageResult } from '../types/common'
import type {
  AssignTaskMembersPayload,
  CreateTaskPayload,
  MyTaskQuery,
  ReviewTaskPayload,
  TaskDetail,
  TaskItem,
  TaskQuery,
  UpdateTaskPayload,
} from '../types/task'
import { request } from './httpClient'

/** 发布任务（团队内）。 */
export function createTask(teamId: number, payload: CreateTaskPayload): Promise<TaskDetail> {
  return request<TaskDetail>('/teams/' + teamId + '/tasks', { method: 'POST', body: payload })
}

/** 团队任务分页列表。 */
export function listTeamTasks(teamId: number, query: TaskQuery): Promise<PageResult<TaskItem>> {
  return request<PageResult<TaskItem>>('/teams/' + teamId + '/tasks', { query: { ...query } })
}

/** 团队任务详情。 */
export function getTeamTask(teamId: number, taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/teams/' + teamId + '/tasks/' + taskId)
}

/** 修改任务（发布者/团队管理员）。 */
export function updateTask(
  teamId: number,
  taskId: number,
  payload: UpdateTaskPayload,
): Promise<TaskDetail> {
  return request<TaskDetail>('/teams/' + teamId + '/tasks/' + taskId, {
    method: 'PUT',
    body: payload,
  })
}

/** 取消任务。 */
export function cancelTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/cancel', { method: 'POST' })
}

/** 接受可选任务。 */
export function acceptTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/acceptance', { method: 'POST' })
}

/** 拒绝可选任务。 */
export function declineTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/decline', { method: 'POST' })
}

/** 标记任务完成（进入待审核）。 */
export function submitTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/submit', { method: 'POST' })
}

/** 审核任务（通过归档/驳回重做）。 */
export function reviewTask(taskId: number, payload: ReviewTaskPayload): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/review', { method: 'POST', body: payload })
}

/** 为无执行人的任务手动指派执行人（发布者/团队管理员；AI 分配失败或改派时使用）。 */
export function assignTaskMembers(
  taskId: number,
  payload: AssignTaskMembersPayload,
): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId + '/assignments', {
    method: 'POST',
    body: payload,
  })
}

/** 任务详情（无需团队 ID）。 */
export function getTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>('/tasks/' + taskId)
}

/** 我的任务中心列表（role=created 我发布的 / assigned 我参与的）。 */
export function listMyTasks(query: MyTaskQuery): Promise<PageResult<TaskItem>> {
  return request<PageResult<TaskItem>>('/tasks', { query: { ...query } })
}