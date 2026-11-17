/** 系统设置接口调用（界面设置、AI 配置与账号注销）。 */

import type { AIConfig, AIConfigTestResult, TestAIConfigPayload, UpdateAIConfigPayload } from '../types/aiConfig'
import type { DeleteAccountPayload } from '../types/auth'
import type { MessageResponse } from '../types/common'
import type { UpdateSettingsPayload, UserSettings } from '../types/setting'
import { request } from './httpClient'

/** 获取当前用户界面设置。 */
export function getSettings(): Promise<UserSettings> {
  return request<UserSettings>('/settings')
}

/** 更新界面设置。 */
export function updateSettings(payload: UpdateSettingsPayload): Promise<UserSettings> {
  return request<UserSettings>('/settings', { method: 'PUT', body: payload })
}

/** 注销账号（密码二次确认）。 */
export function deleteAccount(payload: DeleteAccountPayload): Promise<MessageResponse> {
  return request<MessageResponse>('/settings/account', { method: 'DELETE', body: payload })
}

/** 读取有效 AI 配置（所有登录用户；非管理员 canEdit=false 且 apiKeyMasked=null）。 */
export function getAIConfig(): Promise<AIConfig> {
  return request<AIConfig>('/settings/ai-config')
}

/** 更新 AI 配置（仅全局管理员，字段部分更新；返回最新配置）。 */
export function updateAIConfig(payload: UpdateAIConfigPayload): Promise<AIConfig> {
  return request<AIConfig>('/settings/ai-config', { method: 'PUT', body: payload })
}

/** 连通性测试（仅全局管理员；可用当前表单草稿测试，不修改已保存配置）。 */
export function testAIConfigConnection(payload: TestAIConfigPayload): Promise<AIConfigTestResult> {
  return request<AIConfigTestResult>('/settings/ai-config/test', { method: 'POST', body: payload })
}
