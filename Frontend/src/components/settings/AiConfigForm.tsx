/**
 * AI 配置编辑表单（仅全局管理员）：保存配置或使用当前草稿测试连通性。
 *
 * 交互约定：
 * 1. 保存与测试都先做前端校验，失败时按字段展示中文提示；
 * 2. 测试使用当前表单草稿且不会保存配置；成功用 toast 提示，失败原因由结果区红字展示；
 * 3. 保存成功后回传后端最新配置，由父组件刷新只读状态与 API Key 掩码。
 */

import { useState } from 'react'

import { testAIConfigConnection, updateAIConfig } from '../../api/settingApi'
import { useToast } from '../../context/ToastContext'
import { getErrorMessage } from '../../hooks/errorMessage'
import {
  DISPATCH_MODE_OPTIONS,
  isAssignmentDispatchMode,
  useAiConfigForm,
} from '../../hooks/useAiConfigForm'
import type { AIConfig, AIConfigTestResult } from '../../types/aiConfig'
import Button from '../ui/Button'
import Checkbox from '../ui/Checkbox'
import Input from '../ui/Input'
import Select from '../ui/Select'
import AiConfigTestResult from './AiConfigTestResult'
import styles from './AiConfigSection.module.css'

/** 编辑表单属性。 */
export interface AiConfigFormProps {
  /** 当前有效配置（用于初始化草稿与展示掩码）。 */
  config: AIConfig
  /** 保存成功后的回调（携带后端返回的最新配置）。 */
  onSaved: (updatedConfig: AIConfig) => void
}

/** AI 配置编辑表单。 */
export default function AiConfigForm({ config, onSaved }: AiConfigFormProps) {
  const { showToast } = useToast()
  const { draft, errors, updateField, validate, buildPayload } = useAiConfigForm(config)
  const [saving, setSaving] = useState<boolean>(false)
  const [testing, setTesting] = useState<boolean>(false)
  const [testResult, setTestResult] = useState<AIConfigTestResult | null>(null)

  const busy = saving || testing

  /** 切换调度模式：Select 回调值做类型收窄后写回草稿。 */
  const handleDispatchModeChange = (value: string | number): void => {
    if (isAssignmentDispatchMode(value)) {
      updateField('dispatchMode', value)
    }
  }

  /** 勾选清除 Key 时同步清空输入框，避免误提交新 Key。 */
  const handleClearApiKeyChange = (checked: boolean): void => {
    updateField('clearApiKey', checked)
    if (checked) {
      updateField('llmApiKey', '')
    }
  }

  /** 保存配置：成功后回传后端最新配置（含最新掩码）。 */
  const handleSave = async (): Promise<void> => {
    if (!validate()) {
      return
    }
    setSaving(true)
    try {
      const updatedConfig = await updateAIConfig(buildPayload())
      showToast('AI configuration saved', 'success')
      setTestResult(null)
      onSaved(updatedConfig)
    } catch (error) {
      showToast(getErrorMessage(error, 'Failed to save the AI configuration'), 'error')
    } finally {
      setSaving(false)
    }
  }

  /** 使用当前表单草稿测试连通性（不保存配置）。 */
  const handleTest = async (): Promise<void> => {
    if (!validate()) {
      return
    }
    setTesting(true)
    try {
      const result = await testAIConfigConnection(buildPayload())
      setTestResult(result)
      if (result.llm.configured && result.llm.success) {
        const latencyText =
          result.llm.latencyMs === null ? '' : ', latency ' + result.llm.latencyMs + ' ms'
        showToast('LLM connectivity test succeeded' + latencyText, 'success')
      }
    } catch (error) {
      showToast(getErrorMessage(error, 'Connectivity test failed'), 'error')
    } finally {
      setTesting(false)
    }
  }

  /** API Key 占位文案：已配置时提示掩码并说明留空保持不变。 */
  const apiKeyPlaceholder = config.hasApiKey
    ? 'Configured (' + (config.apiKeyMasked ?? '****') + '); leave blank to keep unchanged'
    : 'No API Key configured yet. Enter one.'

  /** API Key 辅助提示：清除状态优先，其次展示当前掩码。 */
  const apiKeyHint = draft.clearApiKey
    ? 'The saved API Key will be cleared after saving'
    : config.hasApiKey
      ? 'Current saved key: ' + (config.apiKeyMasked ?? '****') + '; leave blank to keep unchanged'
      : 'The LLM can be called only after the Base URL, model, and API Key are all set'

  return (
    <form
      className={styles.formBlock}
      onSubmit={(event) => {
        event.preventDefault()
        void handleSave()
      }}
    >
      <div className={styles.formHeader}>
        <h4 className={styles.blockTitle}>Edit Configuration</h4>
        <span className={styles.formHint}>Only global admins can edit. Changes take effect immediately after saving.</span>
      </div>

      <div className={styles.formGrid}>
        <div className={styles.fieldFull}>
          <Select
            label="Dispatch Mode"
            value={draft.dispatchMode}
            onChange={handleDispatchModeChange}
            options={DISPATCH_MODE_OPTIONS}
            hint="Local First / LLM First fall back automatically according to the selected mode"
            disabled={busy}
          />
        </div>

        <div className={styles.fieldFull}>
          <Input
            label="LLM Base URL"
            value={draft.llmBaseUrl}
            onChange={(event) => updateField('llmBaseUrl', event.target.value)}
            placeholder="https://api.deepseek.com"
            hint="Root URL of an OpenAI-compatible service; leave blank to disable the LLM"
            error={errors.llmBaseUrl}
            disabled={busy}
          />
        </div>

        <Input
          label="Chat Path"
          value={draft.llmChatPath}
          onChange={(event) => updateField('llmChatPath', event.target.value)}
          placeholder="/v1/chat/completions"
          hint="Zhipu GLM usually uses /chat/completions"
          error={errors.llmChatPath}
          disabled={busy}
        />

        <Input
          label="Model"
          value={draft.llmModel}
          onChange={(event) => updateField('llmModel', event.target.value)}
          placeholder="deepseek-chat"
          hint="For example: deepseek-chat / glm-4-flash / gpt-4o-mini"
          error={errors.llmModel}
          maxLength={100}
          disabled={busy}
        />

        <div className={styles.fieldFull}>
          <Input
            label="API Key"
            type="password"
            value={draft.llmApiKey}
            onChange={(event) => updateField('llmApiKey', event.target.value)}
            placeholder={apiKeyPlaceholder}
            hint={apiKeyHint}
            autoComplete="new-password"
            disabled={busy || draft.clearApiKey}
          />
          <Checkbox
            checked={draft.clearApiKey}
            onChange={(event) => handleClearApiKeyChange(event.target.checked)}
            label="Clear Saved Key"
            disabled={busy || !config.hasApiKey}
          />
        </div>

        <Input
          label="Timeout (seconds)"
          type="number"
          value={draft.llmTimeoutSeconds}
          onChange={(event) => updateField('llmTimeoutSeconds', event.target.value)}
          placeholder="20"
          hint="Range: 1-120 seconds"
          error={errors.llmTimeoutSeconds}
          disabled={busy}
        />

        <Input
          label="Max Candidates"
          type="number"
          value={draft.llmMaxCandidates}
          onChange={(event) => updateField('llmMaxCandidates', event.target.value)}
          placeholder="20"
          hint="Number of candidates sent to the prompt, range 1-100"
          error={errors.llmMaxCandidates}
          disabled={busy}
        />

        <Input
          label="Match Threshold"
          type="number"
          value={draft.matchThreshold}
          onChange={(event) => updateField('matchThreshold', event.target.value)}
          placeholder="50"
          hint="0-100 points. Candidates below this score are excluded."
          error={errors.matchThreshold}
          disabled={busy}
        />

        <Input
          label="Workload Penalty"
          type="number"
          value={draft.workloadPenalty}
          onChange={(event) => updateField('workloadPenalty', event.target.value)}
          placeholder="5"
          hint="0-100 points deducted per active to-do"
          error={errors.workloadPenalty}
          disabled={busy}
        />
      </div>

      <div className={styles.actions}>
        <Button htmlType="submit" loading={saving} disabled={testing}>
          Save Configuration
        </Button>
        <Button variant="secondary" loading={testing} disabled={saving} onClick={() => void handleTest()}>
          Test Connectivity
        </Button>
        <span className={styles.actionHint}>Testing uses the current form draft and does not save the configuration</span>
      </div>

      {testing ? <p className={styles.testingHint}>Testing connectivity with the current configuration...</p> : null}
      {testResult ? <AiConfigTestResult result={testResult} /> : null}
    </form>
  )
}
