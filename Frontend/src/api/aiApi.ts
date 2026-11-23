/** AI 辅助接口调用（v1.1：本地规则引擎 + LLM 调度）。 */

import type { AiStatus, RecommendAssigneesPayload, RecommendResponse } from '../types/ai'
import { request } from './httpClient'

/** 获取 AI 模块状态（调度模式、LLM 配置、打分参数）。 */
export function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/ai/status')
}

/** 获取任务接收者推荐（返回调度路由、原因与候选列表）。 */
export function recommendAssignees(
  teamId: number,
  payload: RecommendAssigneesPayload,
): Promise<RecommendResponse> {
  return request<RecommendResponse>('/teams/' + teamId + '/ai/recommend-assignees', {
    method: 'POST',
    body: payload,
  })
}
