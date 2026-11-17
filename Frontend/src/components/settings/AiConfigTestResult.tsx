/**
 * AI 连通性测试结果：展示本地规则引擎与 LLM 的测试状态、延迟与错误信息。
 * 失败信息使用低饱和危险色；该结果仅对应当前表单草稿，不修改已保存配置。
 */

import type { AIConfigTestResult } from '../../types/aiConfig'
import { formatDateTime } from '../../utils/formatUtils'
import Badge from '../ui/Badge'
import styles from './AiConfigSection.module.css'

/** 测试结果属性。 */
export interface AiConfigTestResultProps {
  /** 后端返回的连通性测试结果。 */
  result: AIConfigTestResult
}

/** 根据 LLM 测试状态返回徽标文案。 */
function resolveLlmBadgeLabel(configured: boolean, success: boolean): string {
  if (!configured) {
    return 'Not Configured'
  }
  return success ? 'Connected' : 'Connection Failed'
}

/** 连通性测试结果区块。 */
export default function AiConfigTestResult({ result }: AiConfigTestResultProps) {
  const llmSucceeded = result.llm.configured && result.llm.success
  const llmMessageClassName =
    result.llm.configured && !result.llm.success ? styles.testFailure : styles.testMessage

  return (
    <section className={styles.testResult} aria-live="polite">
      <header className={styles.testHeader}>
        <h4 className={styles.testTitle}>Connectivity Test Result</h4>
        <span className={styles.testTime}>Tested at: {formatDateTime(result.testedAt)}</span>
      </header>

      <div className={styles.testRow}>
        <span className={styles.testName}>Local Rule Engine</span>
        <Badge variant={result.local.available ? 'solid' : 'outline'} size="small">
          {result.local.available ? 'Available' : 'Unavailable'}
        </Badge>
        <span className={result.local.available ? styles.testMessage : styles.testFailure}>
          {result.local.message}
        </span>
      </div>

      <div className={styles.testRow}>
        <span className={styles.testName}>LLM</span>
        <Badge variant={llmSucceeded ? 'solid' : 'outline'} size="small">
          {resolveLlmBadgeLabel(result.llm.configured, result.llm.success)}
        </Badge>
        {result.llm.latencyMs !== null ? (
          <span className={styles.testLatency}>Latency: {result.llm.latencyMs} ms</span>
        ) : null}
        <span className={llmMessageClassName}>{result.llm.message}</span>
      </div>

      {result.llm.responsePreview ? (
        <p className={styles.testPreview}>Response preview: {result.llm.responsePreview}</p>
      ) : null}
    </section>
  )
}
