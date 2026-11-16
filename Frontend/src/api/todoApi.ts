/** 待办清单接口调用。 */

import type { PageResult } from '../types/common'
import type { TodoItem, TodoQuery, TodoStats } from '../types/todo'
import { request } from './httpClient'

/** 我的待办分页列表。 */
export function listTodos(query: TodoQuery): Promise<PageResult<TodoItem>> {
  return request<PageResult<TodoItem>>('/todos', { query: { ...query } })
}

/** 我的待办统计。 */
export function getTodoStats(): Promise<TodoStats> {
  return request<TodoStats>('/todos/stats')
}
