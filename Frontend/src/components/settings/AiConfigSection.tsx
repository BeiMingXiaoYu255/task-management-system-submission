/**
 * AI 配置区块：展示 AI 调度与 LLM 配置状态，并为全局管理员提供编辑表单。
 *
 * 权限约定：
 * 1. 所有登录用户都能看到当前配置（非管理员 apiKeyMasked 为 null，仅提示已配置）；
 * 2. 仅 globalRole 为 superAdmin/globalAdmin 且后端 canEdit=true 时展示编辑与测试入口；
 * 3. 加载失败可重试；保存成功后用后端返回值刷新只读状态与掩码。
 */

import { useCallback } from 'react'

import { getAIConfig } from '../../api/settingApi'
import { useAuth } from '../../context/AuthContext'
import { DISPATCH_MODE_LABELS } from '../../hooks/useAiConfigForm'
import { useAsync } from '../../hooks/useAsync'
import type { AIConfig } from '../../types/aiConfig'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import AiConfigForm from './AiConfigForm'
import styles from './AiConfigSection.module.css'

/** 只读状态展示行。 */
interface SummaryRow {
  label: string
  value: string
}

/** 判断当前用户是否全局管理员（超级用户或全局管理员）。 */
function isGlobalAdminRole(globalRole: string | undefined): boolean {
  return globalRole === 'superAdmin' || globalRole === 'globalAdmin'
}

/** 把 AI 配置转换为只读展示行。 */
function buildSummaryRows(config: AIConfig): SummaryRow[] {
  const llmStatus = config.hasApiKey
    ? config.apiKeyMasked !== null
      ? 'Configured (' + config.apiKeyMasked + ')'
      : 'Configured (mask visible to admins only)'
    : 'Not configured'
  return [
    { label: 'Dispatch Mode', value: DISPATCH_MODE_LABELS[config.dispatchMode] },
    { label: 'LLM Status', value: llmStatus },
    { label: 'Model', value: config.llmModel.length > 0 ? config.llmModel : 'Not set' },
    { label: 'Base URL', value: config.llmBaseUrl.length > 0 ? config.llmBaseUrl : 'Not set' },
    { label: 'Chat Path', value: config.llmChatPath.length > 0 ? config.llmChatPath : 'Not set' },
    { label: 'Timeout', value: config.llmTimeoutSeconds + ' seconds' },
    { label: 'Max Candidates', value: config.llmMaxCandidates + ' members' },
    { label: 'Match Threshold', value: config.matchThreshold + ' points' },
    { label: 'Workload Penalty', value: config.workloadPenalty + ' points per active to-do' },
    {
      label: 'Config Source',
      value: config.configSource === 'database' ? 'System Settings (database)' : 'Environment Variables / Defaults',
    },
  ]
}

/** AI 配置区块。 */
export default function AiConfigSection() {
  const { user } = useAuth()
  const { data: config, loading, error, reload, setData } = useAsync<AIConfig>(
    () => getAIConfig(),
    [],
  )

  /** 保存成功后直接用后端返回值刷新只读状态（含 API Key 掩码）。 */
  const handleSaved = useCallback(
    (updatedConfig: AIConfig): void => {
      setData(updatedConfig)
    },
    [setData],
  )

  if (loading) {
    return (
      <div className={styles.stateBox}>
        <Spinner size="small" />
        <span className={styles.stateText}>Loading AI configuration...</span>
      </div>
    )
  }

  if (error !== null) {
    return (
      <div className={styles.errorBox}>
        <p className={styles.errorText}>{error}</p>
        <Button variant="secondary" size="small" onClick={reload}>
          Retry
        </Button>
      </div>
    )
  }

  if (config === null) {
    return (
      <EmptyState
        title="No AI Configuration"
        description="The server did not return an AI configuration. Please try again."
        action={
          <Button variant="secondary" size="small" onClick={reload}>
            Reload
          </Button>
        }
      />
    )
  }

  const summaryRows = buildSummaryRows(config)
  const llmBadgeLabel = config.hasApiKey ? 'LLM Configured' : 'LLM Not Configured'
  const canEdit = isGlobalAdminRole(user?.user.globalRole) && config.canEdit
  const updatedMeta =
    config.updatedAt !== null
      ? 'Last updated: ' +
        (config.updatedByName !== null ? config.updatedByName : 'Unknown user') +
        ' · ' +
        formatDateTime(config.updatedAt)
      : 'Not modified in the UI yet. Environment variables or built-in defaults are in use.'

  return (
    <div className={styles.sectionLayout}>
      <section className={styles.summaryBlock}>
        <div className={styles.summaryHeader}>
          <h3 className={styles.blockTitle}>Current Configuration</h3>
          <div className={styles.badgeRow}>
            <Badge variant={config.hasApiKey ? 'solid' : 'outline'}>{llmBadgeLabel}</Badge>
            <Badge variant="outline">
              {config.configSource === 'database' ? 'Source: System Settings' : 'Source: Environment Variables'}
            </Badge>
          </div>
        </div>
        <dl className={styles.summaryGrid}>
          {summaryRows.map((summaryRow) => (
            <div key={summaryRow.label} className={styles.summaryItem}>
              <dt className={styles.summaryLabel}>{summaryRow.label}</dt>
              <dd className={styles.summaryValue}>{summaryRow.value}</dd>
            </div>
          ))}
        </dl>
        <p className={styles.summaryMeta}>{updatedMeta}</p>
      </section>

      {canEdit ? (
        <AiConfigForm config={config} onSaved={handleSaved} />
      ) : (
        <p className={styles.permissionNotice}>Only global admins can modify the AI configuration</p>
      )}
    </div>
  )
}
