/** AI 辅助模块类型（v1.1：移植 Java AI 自动分配模块后的契约）。 */

import type { TaskPriority } from './common'

/** 调度模式。 */
export type AssignmentDispatchMode = 'LOCAL_ONLY' | 'LLM_ONLY' | 'LOCAL_FIRST' | 'LLM_FIRST'

/** 推荐请求体。 */
export interface RecommendAssigneesPayload {
  title: string
  description?: string | null
  priority: TaskPriority
  targetLevelMin?: number | null
  targetLevelMax?: number | null
  /** 所需技能标签；为空时后端从标题/描述推导 */
  requiredSkillNames?: string[]
  /** 最多返回候选人数 */
  maxCandidates?: number
}

/** 单个推荐结果。 */
export interface RecommendItem {
  userId: number
  username: string
  nickname: string
  levelName: string
  levelOrder: number
  /** 综合得分（本地引擎：命中率×100−负载惩罚；LLM 链路：排名分） */
  score: number
  /** 技能命中率 0-1 */
  matchRatio: number
  matchedSkills: string[]
  activeTasks: number
  reasons: string[]
  route: 'local' | 'llm'
}

/** 推荐响应。 */
export interface RecommendResponse {
  route: 'local' | 'llm' | null
  reason: string
  candidates: RecommendItem[]
}

/** AI 模块状态。 */
export interface AiStatus {
  provider: string
  available: boolean
  dispatchMode: AssignmentDispatchMode
  localAvailable: boolean
  llmConfigured: boolean
  llmModel: string
  matchThreshold: number
  workloadPenalty: number
  description: string
}

/** 手动指派执行人请求体。 */
export interface AssignTaskMembersPayload {
  userIds: number[]
}
