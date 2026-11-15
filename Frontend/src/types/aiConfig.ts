/** AI 配置与连通性测试类型（v1.1.1，对应后端 aiConfigContract）。 */

import type { AssignmentDispatchMode } from './ai'

/** AI 有效配置（apiKey 仅返回掩码）。 */
export interface AIConfig {
  llmBaseUrl: string
  llmChatPath: string
  llmModel: string
  llmTimeoutSeconds: number
  llmMaxCandidates: number
  dispatchMode: AssignmentDispatchMode
  matchThreshold: number
  workloadPenalty: number
  hasApiKey: boolean
  /** 掩码，仅管理员可见；其他用户为 null */
  apiKeyMasked: string | null
  canEdit: boolean
  configSource: 'database' | 'environment'
  updatedAt: string | null
  updatedByName: string | null
}

/** 更新 AI 配置请求体（字段均可选；apiKey 为空字符串表示保持原值）。 */
export interface UpdateAIConfigPayload {
  llmBaseUrl?: string
  llmChatPath?: string
  llmModel?: string
  llmApiKey?: string
  clearApiKey?: boolean
  llmTimeoutSeconds?: number
  llmMaxCandidates?: number
  dispatchMode?: AssignmentDispatchMode
  matchThreshold?: number
  workloadPenalty?: number
}

/** 连通性测试请求体：与更新请求一致，可用表单草稿测试。 */
export type TestAIConfigPayload = UpdateAIConfigPayload

/** 连通性测试结果。 */
export interface AIConfigTestResult {
  testedAt: string
  local: {
    available: boolean
    message: string
  }
  llm: {
    configured: boolean
    success: boolean
    message: string
    latencyMs: number | null
    responsePreview: string | null
  }
}
