/**
 * AI 调度状态面板：展示调度模式、本地引擎、LLM 配置与打分参数。
 *
 * 数据来自 GET /ai/status；compact 模式用于 AI 推荐面板顶部的一行摘要，
 * 完整模式用于通知中心的任务调度状态卡片。加载/错误态均带重试入口。
 */

import { getAiStatus } from '../../api/aiApi'
import { useAsync } from '../../hooks/useAsync'
import type { AiStatus, AssignmentDispatchMode } from '../../types/ai'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import styles from './AiStatusPanel.module.css'

/** 调度模式中文名。 */
const DISPATCH_MODE_LABELS: Record<AssignmentDispatchMode, string> = {
  LOCAL_ONLY: 'Local Only',
  LLM_ONLY: 'LLM Only',
  LOCAL_FIRST: 'Local First',
  LLM_FIRST: 'LLM First',
}

/** 服务提供方中文名。 */
const PROVIDER_LABELS: Record<string, string> = {
  hybrid: 'Hybrid',
  heuristic: 'Rule Engine',
  local: 'Local Rules',
  llm: 'LLM',
}

/** AI 状态面板属性。 */
export interface AiStatusPanelProps {
  /** 是否使用紧凑摘要样式。 */
  compact?: boolean
}

/** 把调度模式转换为中文名。 */
function getDispatchModeLabel(dispatchMode: AssignmentDispatchMode): string {
  return DISPATCH_MODE_LABELS[dispatchMode] ?? dispatchMode
}

/** AI 调度状态面板。 */
export default function AiStatusPanel({ compact = false }: AiStatusPanelProps) {
  const { data, loading, error, reload } = useAsync<AiStatus>(() => getAiStatus(), [])

  if (loading) {
    if (compact) {
      return <p className={styles.compactLine}>Loading AI status...</p>
    }
    return (
      <section className={styles.panel}>
        <div className={styles.stateBox}>
          <Spinner size="small" />
          <span className={styles.hint}>Loading AI status...</span>
        </div>
      </section>
    )
  }

  if (error !== null || data === null) {
    if (compact) {
      return (
        <p className={styles.compactLine} title={error ?? 'AI status is currently unavailable'}>
          AI status is currently unavailable
        </p>
      )
    }
    return (
      <section className={styles.panel}>
        <div className={styles.errorBox}>
          <span className={styles.errorText}>{error ?? 'AI status is currently unavailable'}</span>
          <Button variant="secondary" size="small" onClick={reload}>
            Retry
          </Button>
        </div>
      </section>
    )
  }

  const dispatchModeLabel = getDispatchModeLabel(data.dispatchMode)
  const llmSummary = data.llmConfigured
    ? 'LLM configured' + (data.llmModel ? ' (' + data.llmModel + ')' : '')
    : 'LLM not configured; using the local engine'

  if (compact) {
    return (
      <p className={styles.compactLine}>
        AI dispatch: {dispatchModeLabel} · {llmSummary}
      </p>
    )
  }

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>AI Dispatch Status</h2>
        <Badge variant={data.available ? 'solid' : 'outline'}>
          {data.available ? 'Available' : 'Unavailable'}
        </Badge>
      </header>
      <dl className={styles.grid}>
        <div className={styles.item}>
          <dt className={styles.label}>Dispatch Mode</dt>
          <dd className={styles.value}>{dispatchModeLabel}</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.label}>Local Engine</dt>
          <dd className={styles.value}>{data.localAvailable ? 'Available' : 'Unavailable'}</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.label}>LLM</dt>
          <dd className={styles.value}>{llmSummary}</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.label}>Match Threshold</dt>
          <dd className={styles.value}>{data.matchThreshold} points</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.label}>Workload Penalty</dt>
          <dd className={styles.value}>{data.workloadPenalty} points per active to-do</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.label}>Provider</dt>
          <dd className={styles.value}>{PROVIDER_LABELS[data.provider] ?? data.provider}</dd>
        </div>
      </dl>
      {data.description ? <p className={styles.description}>{data.description}</p> : null}
    </section>
  )
}
