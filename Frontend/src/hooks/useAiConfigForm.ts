/**
 * AI 配置表单 Hook：把服务端有效配置映射为可编辑草稿，并提供中文校验与请求体构造。
 *
 * 设计说明：
 * 1. 数值字段以字符串保存，方便用户清空后重新输入；提交前统一转换为数字并校验范围；
 * 2. API Key 不展示后端返回值，草稿始终为空：留空表示保持原值，勾选清除才发送 clearApiKey；
 * 3. 服务端返回新配置（首次加载 / 保存成功）时重置草稿，确保掩码等状态同步。
 */

import { useCallback, useEffect, useState } from 'react'

import type { AssignmentDispatchMode } from '../types/ai'
import type { AIConfig, UpdateAIConfigPayload } from '../types/aiConfig'

/** 调度模式选项（中文标签）。 */
export const DISPATCH_MODE_OPTIONS: { value: AssignmentDispatchMode; label: string }[] = [
  { value: 'LOCAL_ONLY', label: 'Local Only' },
  { value: 'LLM_ONLY', label: 'LLM Only (returns no candidates on failure)' },
  { value: 'LOCAL_FIRST', label: 'Local First (calls the LLM when there are no candidates)' },
  { value: 'LLM_FIRST', label: 'LLM First (falls back to local on failure)' },
]

/** 调度模式中文名映射（只读状态与下拉框共用）。 */
export const DISPATCH_MODE_LABELS: Record<AssignmentDispatchMode, string> = {
  LOCAL_ONLY: 'Local Only',
  LLM_ONLY: 'LLM Only',
  LOCAL_FIRST: 'Local First',
  LLM_FIRST: 'LLM First',
}

/** 可编辑的 AI 配置草稿。 */
export interface AiConfigDraft {
  dispatchMode: AssignmentDispatchMode
  llmBaseUrl: string
  llmChatPath: string
  llmModel: string
  llmApiKey: string
  clearApiKey: boolean
  llmTimeoutSeconds: string
  llmMaxCandidates: string
  matchThreshold: string
  workloadPenalty: string
}

/** 字段级校验错误（键与草稿字段一致）。 */
export type AiConfigFieldErrors = Partial<Record<keyof AiConfigDraft, string>>

/** 默认草稿：与 aiModuleContract 第 9 节的默认值保持一致。 */
const DEFAULT_DRAFT: AiConfigDraft = {
  dispatchMode: 'LOCAL_FIRST',
  llmBaseUrl: '',
  llmChatPath: '/v1/chat/completions',
  llmModel: '',
  llmApiKey: '',
  clearApiKey: false,
  llmTimeoutSeconds: '20',
  llmMaxCandidates: '20',
  matchThreshold: '50',
  workloadPenalty: '5',
}

/** 判断值是否为合法调度模式（用于 Select 返回值的类型收窄）。 */
export function isAssignmentDispatchMode(value: string | number): value is AssignmentDispatchMode {
  return (
    value === 'LOCAL_ONLY' ||
    value === 'LLM_ONLY' ||
    value === 'LOCAL_FIRST' ||
    value === 'LLM_FIRST'
  )
}

/** 把服务端配置转换为表单草稿（API Key 永远不回填）。 */
function createDraft(config: AIConfig): AiConfigDraft {
  return {
    dispatchMode: config.dispatchMode,
    llmBaseUrl: config.llmBaseUrl,
    llmChatPath: config.llmChatPath.length > 0 ? config.llmChatPath : '/v1/chat/completions',
    llmModel: config.llmModel,
    llmApiKey: '',
    clearApiKey: false,
    llmTimeoutSeconds: String(config.llmTimeoutSeconds),
    llmMaxCandidates: String(config.llmMaxCandidates),
    matchThreshold: String(config.matchThreshold),
    workloadPenalty: String(config.workloadPenalty),
  }
}

/** 校验必填整数范围，返回中文错误或 null。 */
function validateIntegerField(
  rawValue: string,
  min: number,
  max: number,
  fieldLabel: string,
): string | null {
  if (rawValue.trim().length === 0) {
    return 'Enter ' + fieldLabel.toLowerCase()
  }
  const parsedValue = Number(rawValue)
  if (!Number.isFinite(parsedValue) || !Number.isInteger(parsedValue)) {
    return fieldLabel + ' must be an integer'
  }
  if (parsedValue < min || parsedValue > max) {
    return fieldLabel + ' must be between ' + min + ' and ' + max
  }
  return null
}

/** 校验必填数字范围（允许小数），返回中文错误或 null。 */
function validateNumberField(
  rawValue: string,
  min: number,
  max: number,
  fieldLabel: string,
): string | null {
  if (rawValue.trim().length === 0) {
    return 'Enter ' + fieldLabel.toLowerCase()
  }
  const parsedValue = Number(rawValue)
  if (!Number.isFinite(parsedValue)) {
    return fieldLabel + ' must be a number'
  }
  if (parsedValue < min || parsedValue > max) {
    return fieldLabel + ' must be between ' + min + ' and ' + max
  }
  return null
}

/** 校验整张表单，返回所有字段错误。 */
export function validateAiConfigDraft(draft: AiConfigDraft): AiConfigFieldErrors {
  const errors: AiConfigFieldErrors = {}
  const baseUrl = draft.llmBaseUrl.trim()
  if (baseUrl.length > 0 && !/^https?:\/\/\S+$/i.test(baseUrl)) {
    errors.llmBaseUrl = 'Base URL must start with http:// or https://'
  }
  const chatPath = draft.llmChatPath.trim()
  if (chatPath.length === 0) {
    errors.llmChatPath = 'Chat path is required'
  } else if (!chatPath.startsWith('/')) {
    errors.llmChatPath = 'Chat path must start with /'
  }
  if (draft.llmModel.trim().length > 100) {
    errors.llmModel = 'Model name must not exceed 100 characters'
  }
  const timeoutError = validateIntegerField(draft.llmTimeoutSeconds, 1, 120, 'Timeout')
  if (timeoutError !== null) {
    errors.llmTimeoutSeconds = timeoutError
  }
  const candidateError = validateIntegerField(draft.llmMaxCandidates, 1, 100, 'Max Candidates')
  if (candidateError !== null) {
    errors.llmMaxCandidates = candidateError
  }
  const thresholdError = validateNumberField(draft.matchThreshold, 0, 100, 'Match Threshold')
  if (thresholdError !== null) {
    errors.matchThreshold = thresholdError
  }
  const penaltyError = validateNumberField(draft.workloadPenalty, 0, 100, 'Workload Penalty')
  if (penaltyError !== null) {
    errors.workloadPenalty = penaltyError
  }
  return errors
}

/** 把通过校验的草稿转换为更新/测试请求体。 */
export function buildAiConfigPayload(draft: AiConfigDraft): UpdateAIConfigPayload {
  const payload: UpdateAIConfigPayload = {
    dispatchMode: draft.dispatchMode,
    llmBaseUrl: draft.llmBaseUrl.trim().replace(/\/+$/, ''),
    llmChatPath: draft.llmChatPath.trim(),
    llmModel: draft.llmModel.trim(),
    llmTimeoutSeconds: Number(draft.llmTimeoutSeconds),
    llmMaxCandidates: Number(draft.llmMaxCandidates),
    matchThreshold: Number(draft.matchThreshold),
    workloadPenalty: Number(draft.workloadPenalty),
  }
  const apiKey = draft.llmApiKey.trim()
  if (apiKey.length > 0) {
    payload.llmApiKey = apiKey
  }
  if (draft.clearApiKey) {
    payload.clearApiKey = true
  }
  return payload
}

/** AI 配置表单状态与操作。 */
export interface AiConfigFormState {
  draft: AiConfigDraft
  errors: AiConfigFieldErrors
  updateField: <TField extends keyof AiConfigDraft>(
    field: TField,
    value: AiConfigDraft[TField],
  ) => void
  validate: () => boolean
  buildPayload: () => UpdateAIConfigPayload
}

/**
 * 创建 AI 配置表单状态。
 *
 * @param config 服务端返回的有效配置；变化时重置草稿
 * @returns 草稿、错误、字段更新、校验与请求体构造
 */
export function useAiConfigForm(config: AIConfig | null): AiConfigFormState {
  const [draft, setDraft] = useState<AiConfigDraft>(DEFAULT_DRAFT)
  const [errors, setErrors] = useState<AiConfigFieldErrors>({})

  useEffect(() => {
    if (config !== null) {
      setDraft(createDraft(config))
      setErrors({})
    }
  }, [config])

  /** 更新单个字段，并清除该字段的旧错误。 */
  const updateField = useCallback(
    <TField extends keyof AiConfigDraft>(field: TField, value: AiConfigDraft[TField]): void => {
      setDraft((previousDraft) => ({ ...previousDraft, [field]: value }))
      setErrors((previousErrors) => {
        if (previousErrors[field] === undefined) {
          return previousErrors
        }
        const nextErrors = { ...previousErrors }
        delete nextErrors[field]
        return nextErrors
      })
    },
    [],
  )

  /** 校验全部字段；返回是否通过。 */
  const validate = useCallback((): boolean => {
    const nextErrors = validateAiConfigDraft(draft)
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }, [draft])

  /** 构造当前草稿对应的请求体。 */
  const buildPayload = useCallback((): UpdateAIConfigPayload => buildAiConfigPayload(draft), [draft])

  return { draft, errors, updateField, validate, buildPayload }
}
